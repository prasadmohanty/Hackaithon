"""Application service: the use-cases exposed by the API.

The service coordinates repositories (persistence), domain models
(validation), the analyser, the recommendation engine and the report
builders. The HTTP layer only translates requests to these method calls,
so the same service could back a CLI, a GUI or tests.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from typing import Dict, List, Optional, Tuple

from . import __version__
from .analytics import PerformanceAnalyzer, StudentPerformance
from .config import SETTINGS_SPEC
from .constants import (ACCESSIBILITY_FORMATS, ASSESSMENT_TYPES, DIFFICULTY_LEVELS,
                        RESOURCE_CATEGORIES, TOPIC_STATUSES)
from .database import (AssessmentRepository, Database, ResourceRepository, SettingsRepository,
                       StudentRepository, SubjectRepository, TopicRepository, ValidationLogRepository)
from .models import (Assessment, ConflictError, NotFoundError, Resource, Student, Subject, Topic,
                     ValidationError, field_error)
from .recommender import SELECTION_POLICY, RecommendationEngine
from .reports import ClassSummaryBuilder, LearnerReportBuilder


def _int_or_none(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class Learn4AllService:
    def __init__(self, db: Database):
        self.db = db
        self.students = StudentRepository(db)
        self.subjects = SubjectRepository(db)
        self.topics = TopicRepository(db)
        self.assessments = AssessmentRepository(db)
        self.resources = ResourceRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.validation_log = ValidationLogRepository(db)

    # ======================================================================
    # Meta & settings
    # ======================================================================
    def meta(self) -> dict:
        return {
            "name": "Learn4All API",
            "version": __version__,
            "resource_categories": list(RESOURCE_CATEGORIES),
            "difficulty_levels": list(DIFFICULTY_LEVELS),
            "assessment_types": list(ASSESSMENT_TYPES),
            "accessibility_formats": [{"code": k, "description": v} for k, v in ACCESSIBILITY_FORMATS.items()],
            "topic_statuses": [{"code": k, "description": v} for k, v in TOPIC_STATUSES.items()],
            "counts": {"students": self.students.count(), "subjects": self.subjects.count(),
                       "topics": self.topics.count(), "assessments": self.assessments.count(),
                       "resources": self.resources.count()},
        }

    def get_settings(self) -> dict:
        values = self.settings_repo.get_all()
        return {"values": values,
                "spec": {k: {**v, "value": values[k]} for k, v in SETTINGS_SPEC.items()}}

    def update_settings(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValidationError([field_error("body", "Settings must be a JSON object")])
        payload = payload.get("values", payload)
        current = self.settings_repo.get_all()
        errors, changes = [], {}
        for key, raw in payload.items():
            spec = SETTINGS_SPEC.get(key)
            if spec is None:
                errors.append(field_error(key, "Unknown setting"))
                continue
            try:
                value = int(raw) if spec["type"] == "int" else float(raw)
                if spec["type"] == "int" and float(raw) != int(raw):
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(field_error(key, f"Must be a{'n integer' if spec['type'] == 'int' else ' number'}"))
                continue
            if not spec["min"] <= value <= spec["max"]:
                errors.append(field_error(key, f"Must be between {spec['min']} and {spec['max']}"))
                continue
            changes[key] = value
        merged = {**current, **changes}
        if merged["weak_threshold"] >= merged["mastery_threshold"]:
            errors.append(field_error("weak_threshold", "Weak threshold must be lower than mastery threshold"))
        if errors:
            raise ValidationError(errors)
        self.settings_repo.save(changes)
        return self.get_settings()

    def reset_settings(self) -> dict:
        self.settings_repo.reset()
        return self.get_settings()

    def rules(self) -> dict:
        settings = self.settings_repo.get_all()
        engine = RecommendationEngine(settings)
        return {
            "status_definitions": [{"code": k, "description": v} for k, v in TOPIC_STATUSES.items()],
            "status_rules": [
                f"No assessments -> no_data.",
                f"Weighted average < {settings['weak_threshold']:g}% with >= {settings['min_evidence']} "
                f"results -> weak (confirmed by history).",
                f"Weighted average < {settings['weak_threshold']:g}% with fewer results -> at_risk "
                f"(limited evidence; a single low score is not enough to confirm).",
                f"Declining trend and latest score < {settings['weak_threshold']:g}% -> at_risk.",
                f"Weighted average >= {settings['mastery_threshold']:g}% with enough evidence and no "
                f"decline -> mastered (otherwise proficient).",
                f"Between thresholds: below the midpoint -> developing, otherwise proficient.",
            ],
            "formulas": {
                "percentage": "score / max_score * 100",
                "weighted_average": "sum(w_i * p_i) / sum(w_i); w_i = type_weight * (1 + recency_weight * i)",
                "trend": f"least-squares slope; >= +{settings['trend_threshold']:g} improving, "
                         f"<= -{settings['trend_threshold']:g} declining, else stable",
                "improvement_rate": "(latest - first) / first * 100",
                "priority": "(mastery - weighted_avg) * severity(weak 1.0, at_risk 0.8, developing 0.5) "
                            "+ 10 if declining",
            },
            "recommendation_rules": engine.describe_rules(),
            "selection_policy": SELECTION_POLICY,
            "settings": settings,
        }

    # ======================================================================
    # Lookups
    # ======================================================================
    def _lookups(self) -> Tuple[Dict[int, Topic], Dict[int, Subject]]:
        return ({t.id: t for t in self.topics.list()}, {s.id: s for s in self.subjects.list()})

    def _require(self, repo, entity_id: int, label: str):
        entity = repo.get(entity_id)
        if entity is None:
            raise NotFoundError(f"{label} {entity_id} not found")
        return entity

    # ======================================================================
    # Students
    # ======================================================================
    def _performance(self, student: Student, lookups=None, settings=None) -> StudentPerformance:
        topics_by_id, subjects_by_id = lookups or self._lookups()
        analyzer = PerformanceAnalyzer(settings or self.settings_repo.get_all())
        assessments = self.assessments.list(student_id=student.id)
        student.load_assessments(assessments)
        return analyzer.analyse_student(assessments, topics_by_id, subjects_by_id)

    def _student_summary(self, student: Student, lookups, settings) -> dict:
        perf = self._performance(student, lookups, settings)
        data = student.to_dict()
        data["summary"] = {
            "overall_average": perf.overall_average, "trend": perf.overall_trend,
            "assessment_count": perf.assessment_count, "gap_count": len(perf.gaps),
            "strength_count": len(perf.strengths),
            "band": LearnerReportBuilder(settings).band(perf.overall_average),
        }
        return data

    def list_students(self, search: Optional[str] = None) -> List[dict]:
        lookups, settings = self._lookups(), self.settings_repo.get_all()
        return [self._student_summary(s, lookups, settings) for s in self.students.list(search)]

    def get_student(self, student_id: int) -> dict:
        student = self._require(self.students, student_id, "Student")
        return self._student_summary(student, self._lookups(), self.settings_repo.get_all())

    def _save_student(self, student: Student, existing_id: Optional[int] = None) -> dict:
        student.ensure_valid()
        if student.email:
            other = self.students.find_by_email(student.email)
            if other and other.id != existing_id:
                raise ConflictError("Email already in use", [field_error("email", "Email already registered")])
        saved = self.students.update(student) if existing_id else self.students.add(student)
        return self.get_student(saved.id)

    def create_student(self, payload: dict) -> dict:
        payload = payload if isinstance(payload, dict) else {}
        return self._save_student(Student(**self._student_fields(payload)))

    def update_student(self, student_id: int, payload: dict) -> dict:
        current = self._require(self.students, student_id, "Student").to_dict()
        merged = {**current, **(payload if isinstance(payload, dict) else {})}
        student = Student(**self._student_fields(merged), id=student_id)
        return self._save_student(student, existing_id=student_id)

    @staticmethod
    def _student_fields(p: dict) -> dict:
        return {
            "name": p.get("name"), "email": p.get("email"), "grade_level": p.get("grade_level") or "",
            "accessibility_needs": p.get("accessibility_needs") or [],
            "preferred_categories": p.get("preferred_categories") or [],
            "weekly_study_minutes": p.get("weekly_study_minutes", 120), "notes": p.get("notes") or ""}

    def delete_student(self, student_id: int) -> dict:
        self._require(self.students, student_id, "Student")
        self.students.delete(student_id)
        return {"deleted": True, "id": student_id}

    # ======================================================================
    # Subjects & topics
    # ======================================================================
    def list_subjects(self, include_topics: bool = True) -> List[dict]:
        topics = self.topics.list()
        result = []
        for s in self.subjects.list():
            s.load_topics(t for t in topics if t.subject_id == s.id)
            result.append(s.to_dict(include_topics=include_topics))
        return result

    def get_subject(self, subject_id: int) -> dict:
        s = self._require(self.subjects, subject_id, "Subject")
        s.load_topics(self.topics.list(subject_id))
        return s.to_dict(include_topics=True)

    def create_subject(self, payload: dict) -> dict:
        payload = payload if isinstance(payload, dict) else {}
        subject = Subject(payload.get("code"), payload.get("name"), payload.get("description"))
        subject.ensure_valid()
        if self.subjects.find_by_code(subject.code):
            raise ConflictError("Subject code already exists", [field_error("code", "Code must be unique")])
        saved = self.subjects.add(subject)
        for name in payload.get("topics") or []:
            self.create_topic(saved.id, {"name": name} if isinstance(name, str) else name)
        return self.get_subject(saved.id)

    def update_subject(self, subject_id: int, payload: dict) -> dict:
        current = self._require(self.subjects, subject_id, "Subject").to_dict()
        merged = {**current, **(payload if isinstance(payload, dict) else {})}
        subject = Subject(merged.get("code"), merged.get("name"), merged.get("description"), id=subject_id)
        subject.ensure_valid()
        other = self.subjects.find_by_code(subject.code)
        if other and other.id != subject_id:
            raise ConflictError("Subject code already exists", [field_error("code", "Code must be unique")])
        self.subjects.update(subject)
        return self.get_subject(subject_id)

    def delete_subject(self, subject_id: int) -> dict:
        self._require(self.subjects, subject_id, "Subject")
        self.subjects.delete(subject_id)
        return {"deleted": True, "id": subject_id}

    def list_topics(self, subject_id: Optional[int] = None) -> List[dict]:
        subjects = {s.id: s for s in self.subjects.list()}
        return [{**t.to_dict(), "subject_name": subjects[t.subject_id].name,
                 "subject_code": subjects[t.subject_id].code}
                for t in self.topics.list(subject_id)]

    def create_topic(self, subject_id: int, payload: dict) -> dict:
        subject = self._require(self.subjects, subject_id, "Subject")
        payload = payload if isinstance(payload, dict) else {}
        subject.load_topics(self.topics.list(subject_id))
        topic = subject.add_topic(Topic(subject_id, payload.get("name"), payload.get("description")))
        topic.ensure_valid()
        return self.topics.add(topic).to_dict()

    def update_topic(self, topic_id: int, payload: dict) -> dict:
        current = self._require(self.topics, topic_id, "Topic").to_dict()
        merged = {**current, **(payload if isinstance(payload, dict) else {})}
        topic = Topic(_int_or_none(merged.get("subject_id")), merged.get("name"),
                      merged.get("description"), id=topic_id)
        topic.ensure_valid()
        self._require(self.subjects, topic.subject_id, "Subject")
        other = self.topics.find(topic.subject_id, topic.name)
        if other and other.id != topic_id:
            raise ConflictError("Topic already exists in subject", [field_error("name", "Must be unique")])
        return self.topics.update(topic).to_dict()

    def delete_topic(self, topic_id: int) -> dict:
        self._require(self.topics, topic_id, "Topic")
        self.topics.delete(topic_id)
        return {"deleted": True, "id": topic_id}

    # ======================================================================
    # Assessments
    # ======================================================================
    def _enrich_assessments(self, items: List[Assessment]) -> List[dict]:
        topics_by_id, subjects_by_id = self._lookups()
        names = {s.id: s.name for s in self.students.list()}
        result = []
        for a in items:
            d = a.to_dict()
            t = topics_by_id.get(a.topic_id)
            d["topic_name"] = t.name if t else None
            d["subject_id"] = t.subject_id if t else None
            d["subject_name"] = subjects_by_id[t.subject_id].name if t else None
            d["student_name"] = names.get(a.student_id)
            result.append(d)
        return result

    def list_assessments(self, **filters) -> List[dict]:
        return self._enrich_assessments(self.assessments.list(**filters))

    def get_assessment(self, assessment_id: int) -> dict:
        return self._enrich_assessments([self._require(self.assessments, assessment_id, "Assessment")])[0]

    def _resolve_references(self, payload: dict) -> Tuple[dict, List[dict]]:
        """Allow student_email and subject_code/subject_id + topic_name instead of raw ids."""
        data, errors = dict(payload), []
        if data.get("student_id") in (None, "") and data.get("student_email"):
            s = self.students.find_by_email(data["student_email"])
            if s:
                data["student_id"] = s.id
            else:
                errors.append(field_error("student_email", f"Unknown student '{data['student_email']}'"))
        if data.get("topic_id") in (None, "") and data.get("topic_name"):
            subject = (self.subjects.find_by_code(data["subject_code"]) if data.get("subject_code")
                       else self.subjects.get(_int_or_none(data.get("subject_id")) or -1))
            topic = self.topics.find(subject.id, data["topic_name"]) if subject else None
            if topic:
                data["topic_id"] = topic.id
            else:
                errors.append(field_error("topic_name", f"Unknown topic '{data['topic_name']}' "
                                                         f"for the given subject"))
        return data, errors

    def _prepare_assessment(self, payload: dict, existing_id: Optional[int] = None) -> Assessment:
        if not isinstance(payload, dict):
            raise ValidationError([field_error("body", "Assessment must be a JSON object")])
        data, errors = self._resolve_references(payload)
        assessment = Assessment.from_payload(data)
        if existing_id:
            assessment.id = existing_id
        errors += [e for e in assessment.validate()
                   if not (e["field"] in ("student_id", "topic_id") and any(
                       x["field"] in ("student_email", "topic_name") for x in errors))]
        if isinstance(assessment.student_id, int) and not self.students.get(assessment.student_id):
            errors.append(field_error("student_id", f"Student {assessment.student_id} does not exist"))
        if isinstance(assessment.topic_id, int):
            topic = self.topics.get(assessment.topic_id)
            if not topic:
                errors.append(field_error("topic_id", f"Topic {assessment.topic_id} does not exist"))
            elif data.get("subject_id") not in (None, "") and _int_or_none(data["subject_id"]) != topic.subject_id:
                errors.append(field_error("subject_id", f"Topic '{topic.name}' does not belong to subject "
                                                        f"{data['subject_id']} (inconsistent)"))
        if errors:
            raise ValidationError(errors)
        duplicate = self.assessments.find_duplicate(assessment)
        if duplicate:
            raise ConflictError(
                "Duplicate assessment: the same student, topic, date and type already exists",
                [field_error("date", f"Duplicate of assessment #{duplicate.id}")])
        return assessment

    def _log_rejection(self, source: str, payload, error) -> None:
        student_id = _int_or_none(payload.get("student_id")) if isinstance(payload, dict) else None
        if student_id is None and isinstance(payload, dict) and payload.get("student_email"):
            s = self.students.find_by_email(payload["student_email"])
            student_id = s.id if s else None
        if student_id is not None and not self.students.get(student_id):
            student_id = None
        details = error.details or [field_error("general", error.message)]
        if isinstance(error, ConflictError):
            details = [dict(d, message=f"{error.message}. {d['message']}") for d in details]
        self.validation_log.add(source, payload, details, student_id)

    def create_assessment(self, payload: dict, source: str = "api") -> dict:
        try:
            assessment = self._prepare_assessment(payload)
            return self.get_assessment(self.assessments.add(assessment).id)
        except (ValidationError, ConflictError) as exc:
            self._log_rejection(source, payload, exc)
            raise

    def bulk_create_assessments(self, payload, source: str = "bulk") -> dict:
        rows = self._bulk_rows(payload)
        results, accepted = [], 0
        for index, row in enumerate(rows, start=1):
            try:
                created = self.create_assessment(row, source=source)
                accepted += 1
                results.append({"row": index, "status": "created", "id": created["id"]})
            except (ValidationError, ConflictError) as exc:
                results.append({"row": index, "status": "rejected", "code": exc.code,
                                "errors": exc.details or [field_error("general", exc.message)]})
        return {"total": len(rows), "accepted": accepted, "rejected": len(rows) - accepted,
                "results": results}

    @staticmethod
    def _bulk_rows(payload) -> List[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            return payload["rows"]
        if isinstance(payload, dict) and isinstance(payload.get("csv"), str):
            reader = csv.DictReader(io.StringIO(payload["csv"].strip()))
            return [{k.strip(): (v.strip() if isinstance(v, str) else v)
                     for k, v in row.items() if k} for row in reader]
        raise ValidationError([field_error("body", "Send a list, {'rows': [...]} or {'csv': 'text'}")])

    def update_assessment(self, assessment_id: int, payload: dict) -> dict:
        current = self._require(self.assessments, assessment_id, "Assessment").to_dict()
        merged = {**current, **(payload if isinstance(payload, dict) else {})}
        assessment = self._prepare_assessment(merged, existing_id=assessment_id)
        self.assessments.update(assessment)
        return self.get_assessment(assessment_id)

    def delete_assessment(self, assessment_id: int) -> dict:
        self._require(self.assessments, assessment_id, "Assessment")
        self.assessments.delete(assessment_id)
        return {"deleted": True, "id": assessment_id}

    # ======================================================================
    # Resources
    # ======================================================================
    def _enrich_resources(self, items: List[Resource]) -> List[dict]:
        topics_by_id, subjects_by_id = self._lookups()
        out = []
        for r in items:
            d = r.to_dict()
            t = topics_by_id.get(r.topic_id)
            d["topic_name"] = t.name if t else None
            d["subject_id"] = t.subject_id if t else None
            d["subject_name"] = subjects_by_id[t.subject_id].name if t else None
            out.append(d)
        return out

    def list_resources(self, **filters) -> List[dict]:
        return self._enrich_resources(self.resources.list(**filters))

    def get_resource(self, resource_id: int) -> dict:
        return self._enrich_resources([self._require(self.resources, resource_id, "Resource")])[0]

    def _build_resource(self, p: dict, resource_id: Optional[int] = None) -> Resource:
        if not isinstance(p, dict):
            raise ValidationError([field_error("body", "Resource must be a JSON object")])
        resource = Resource.create(
            p.get("category"), title=p.get("title"), topic_id=p.get("topic_id"),
            difficulty=p.get("difficulty"), estimated_minutes=p.get("estimated_minutes"),
            formats=p.get("formats") or [], url=p.get("url") or "",
            description=p.get("description") or "", id=resource_id)
        resource.ensure_valid()
        if not self.topics.get(resource.topic_id):
            raise ValidationError([field_error("topic_id", f"Topic {resource.topic_id} does not exist")])
        return resource

    def create_resource(self, payload: dict) -> dict:
        return self.get_resource(self.resources.add(self._build_resource(payload)).id)

    def update_resource(self, resource_id: int, payload: dict) -> dict:
        current = self._require(self.resources, resource_id, "Resource").to_dict()
        merged = {**current, **(payload if isinstance(payload, dict) else {})}
        self.resources.update(self._build_resource(merged, resource_id))
        return self.get_resource(resource_id)

    def delete_resource(self, resource_id: int) -> dict:
        self._require(self.resources, resource_id, "Resource")
        self.resources.delete(resource_id)
        return {"deleted": True, "id": resource_id}

    # ======================================================================
    # Analytics, recommendations & reports
    # ======================================================================
    def student_performance(self, student_id: int) -> dict:
        student = self._require(self.students, student_id, "Student")
        return {"student": student.to_dict(), **self._performance(student).to_dict()}

    def _plan(self, student: Student, settings, lookups) -> Tuple[StudentPerformance, dict]:
        perf = self._performance(student, lookups, settings)
        topic_names = {tid: t.name for tid, t in lookups[0].items()}
        plan = RecommendationEngine(settings).recommend(student, perf, self.resources.list(), topic_names)
        return perf, plan

    def student_recommendations(self, student_id: int) -> dict:
        student = self._require(self.students, student_id, "Student")
        _, plan = self._plan(student, self.settings_repo.get_all(), self._lookups())
        return {"student": student.to_dict(), **plan}

    def learner_report(self, student_id: int) -> dict:
        student = self._require(self.students, student_id, "Student")
        settings, lookups = self.settings_repo.get_all(), self._lookups()
        perf, plan = self._plan(student, settings, lookups)
        rules = plan.pop("rules")
        return LearnerReportBuilder(settings).build(
            student, perf, plan, self.validation_log.list(student_id), rules)

    def class_summary(self) -> dict:
        settings, lookups = self.settings_repo.get_all(), self._lookups()
        issues = self.validation_log.list()
        per_student = {}
        for entry in issues:
            if entry["student_id"]:
                per_student[entry["student_id"]] = per_student.get(entry["student_id"], 0) + 1
        rows = [{"student": s, "performance": self._performance(s, lookups, settings),
                 "issues": per_student.get(s.id, 0)} for s in self.students.list()]
        return ClassSummaryBuilder(settings).build(rows, self.resources.count(), len(issues))

    # ======================================================================
    # Data quality log & admin
    # ======================================================================
    def list_validation_log(self, student_id: Optional[int] = None) -> List[dict]:
        names = {s.id: s.name for s in self.students.list()}
        return [{**e, "student_name": names.get(e["student_id"])}
                for e in self.validation_log.list(student_id)]

    def delete_validation_entry(self, entry_id: int) -> dict:
        if not self.validation_log.delete(entry_id):
            raise NotFoundError(f"Log entry {entry_id} not found")
        return {"deleted": True, "id": entry_id}

    def clear_validation_log(self, student_id: Optional[int] = None) -> dict:
        return {"deleted": self.validation_log.clear(student_id)}

    def reset_demo_data(self) -> dict:
        from .seed import seed_demo_data
        self.db.drop_all()
        self.db.initialize()
        return seed_demo_data(self)
