"""Endpoint table: maps HTTP method + path to service use-cases.

Conventions
-----------
* Collection endpoints return ``{"items": [...], "count": n}``.
* Single resources are returned as plain JSON objects.
* Errors return ``{"error": {"code", "message", "details": [{field, message}]}}``
  with status 400/404/405/409/422/500.
* PUT and PATCH both perform partial updates (only the fields sent change).
"""

from __future__ import annotations

from .. import __version__
from ..services import Learn4AllService
from .router import Request, Router

STUDENT_BODY = {"name": "Asha Rao", "email": "asha@school.example", "grade_level": "Grade 8",
                "accessibility_needs": ["captions"], "preferred_categories": ["video"],
                "weekly_study_minutes": 120, "notes": ""}
SUBJECT_BODY = {"code": "SCI8", "name": "Science", "description": "Grade 8 science",
                "topics": ["Cells", "Forces"]}
TOPIC_BODY = {"name": "Probability", "description": "Chance and likelihood"}
ASSESSMENT_BODY = {"student_id": 1, "topic_id": 4, "date": "2026-10-01", "score": 72,
                   "max_score": 100, "assessment_type": "test", "notes": ""}
BULK_BODY = {"csv": "student_email,subject_code,topic_name,date,score,max_score,assessment_type\n"
                    "mira@learn4all.example,PY101,Loops,2026-10-10,61,100,quiz"}
RESOURCE_BODY = {"title": "Loops Recap", "topic_id": 4, "category": "notes", "difficulty": "beginner",
                 "estimated_minutes": 15, "formats": ["screen-reader"],
                 "url": "https://example.org/loops", "description": ""}
SETTINGS_BODY = {"weak_threshold": 60, "mastery_threshold": 85, "min_evidence": 2}


def items(data: list) -> dict:
    return {"items": data, "count": len(data)}


def build_router(service: Learn4AllService) -> Router:
    r = Router()
    s = service

    # --- system ---------------------------------------------------------------------
    r.add("GET", "/api/health", lambda q: {"status": "ok", "version": __version__},
          "Health check", "System")
    r.add("GET", "/api/meta", lambda q: s.meta(),
          "Vocabularies (categories, difficulties, formats, statuses) and record counts", "System")
    r.add("GET", "/api/docs", lambda q: {"endpoints": r.describe()},
          "Human-readable list of all endpoints", "System")
    r.add("POST", "/api/admin/reset", lambda q: s.reset_demo_data(),
          "Erase the database and reload the sample data", "System")

    # --- settings & rules ---------------------------------------------------------------
    r.add("GET", "/api/settings", lambda q: s.get_settings(), "Current analysis settings + spec", "Settings")
    r.add("PUT", "/api/settings", lambda q: s.update_settings(q.body), "Update settings (partial)",
          "Settings", body=SETTINGS_BODY)
    r.add("POST", "/api/settings/reset", lambda q: s.reset_settings(), "Restore default settings", "Settings")
    r.add("GET", "/api/rules", lambda q: s.rules(),
          "Explain status rules, formulas and recommendation rules", "Settings")

    # --- students -----------------------------------------------------------------
    r.add("GET", "/api/students", lambda q: items(s.list_students(q.q_str("search"))),
          "List students with a performance summary", "Students", query=[("search", "Name/email contains")])
    r.add("POST", "/api/students", lambda q: s.create_student(q.body), "Create a student", "Students",
          status=201, body=STUDENT_BODY)
    r.add("GET", "/api/students/{id}", lambda q: s.get_student(q.params["id"]), "Get a student", "Students")
    r.add("PUT", "/api/students/{id}", lambda q: s.update_student(q.params["id"], q.body),
          "Update a student", "Students", body=STUDENT_BODY)
    r.add("PATCH", "/api/students/{id}", lambda q: s.update_student(q.params["id"], q.body),
          "Update a student (alias of PUT)", "Students", body={"weekly_study_minutes": 90})
    r.add("DELETE", "/api/students/{id}", lambda q: s.delete_student(q.params["id"]),
          "Delete a student and their records", "Students")
    r.add("GET", "/api/students/{id}/assessments",
          lambda q: items(s.list_assessments(student_id=q.params["id"])), "A student's assessments", "Students")
    r.add("GET", "/api/students/{id}/performance", lambda q: s.student_performance(q.params["id"]),
          "Performance indicators: subject/topic averages, trends, statuses, timeline", "Analytics")
    r.add("GET", "/api/students/{id}/recommendations", lambda q: s.student_recommendations(q.params["id"]),
          "Personalised, explainable resource plan", "Analytics")
    r.add("GET", "/api/students/{id}/report", lambda q: s.learner_report(q.params["id"]),
          "Full individual learner report", "Reports")
    r.add("GET", "/api/students/{id}/validation-log",
          lambda q: items(s.list_validation_log(q.params["id"])), "Rejected records for a student",
          "Data quality")

    # --- subjects & topics -------------------------------------------------------------
    r.add("GET", "/api/subjects", lambda q: items(s.list_subjects(q.q_bool("include_topics", True))),
          "List subjects (with topics)", "Subjects", query=[("include_topics", "true/false (default true)")])
    r.add("POST", "/api/subjects", lambda q: s.create_subject(q.body), "Create a subject (optionally with topics)",
          "Subjects", status=201, body=SUBJECT_BODY)
    r.add("GET", "/api/subjects/{id}", lambda q: s.get_subject(q.params["id"]), "Get a subject", "Subjects")
    r.add("PUT", "/api/subjects/{id}", lambda q: s.update_subject(q.params["id"], q.body), "Update a subject",
          "Subjects", body={"name": "Python Programming I"})
    r.add("DELETE", "/api/subjects/{id}", lambda q: s.delete_subject(q.params["id"]),
          "Delete a subject (cascades topics, assessments, resources)", "Subjects")
    r.add("GET", "/api/subjects/{id}/topics", lambda q: items(s.list_topics(q.params["id"])),
          "Topics of a subject", "Subjects")
    r.add("POST", "/api/subjects/{id}/topics", lambda q: s.create_topic(q.params["id"], q.body),
          "Add a topic to a subject", "Subjects", status=201, body=TOPIC_BODY)
    r.add("GET", "/api/topics", lambda q: items(s.list_topics(q.q_int("subject_id"))), "List all topics",
          "Subjects", query=[("subject_id", "Filter by subject")])
    r.add("PUT", "/api/topics/{id}", lambda q: s.update_topic(q.params["id"], q.body), "Update a topic",
          "Subjects", body=TOPIC_BODY)
    r.add("DELETE", "/api/topics/{id}", lambda q: s.delete_topic(q.params["id"]), "Delete a topic", "Subjects")

    # --- assessments ---------------------------------------------------------------------
    r.add("GET", "/api/assessments",
          lambda q: items(s.list_assessments(student_id=q.q_int("student_id"), topic_id=q.q_int("topic_id"),
                                             subject_id=q.q_int("subject_id"), date_from=q.q_str("from"),
                                             date_to=q.q_str("to"))),
          "List assessments", "Assessments",
          query=[("student_id", "Filter by student"), ("topic_id", "Filter by topic"),
                 ("subject_id", "Filter by subject"), ("from", "YYYY-MM-DD"), ("to", "YYYY-MM-DD")])
    r.add("POST", "/api/assessments", lambda q: s.create_assessment(q.body),
          "Record an assessment (validated: missing/invalid/duplicate/inconsistent)", "Assessments",
          status=201, body=ASSESSMENT_BODY)
    r.add("POST", "/api/assessments/bulk", lambda q: s.bulk_create_assessments(q.body),
          "Bulk import from JSON rows or CSV text; returns per-row results", "Assessments", body=BULK_BODY)
    r.add("GET", "/api/assessments/{id}", lambda q: s.get_assessment(q.params["id"]), "Get an assessment",
          "Assessments")
    r.add("PUT", "/api/assessments/{id}", lambda q: s.update_assessment(q.params["id"], q.body),
          "Update an assessment", "Assessments", body={"score": 75})
    r.add("DELETE", "/api/assessments/{id}", lambda q: s.delete_assessment(q.params["id"]),
          "Delete an assessment", "Assessments")

    # --- resources -------------------------------------------------------------------------
    r.add("GET", "/api/resources",
          lambda q: items(s.list_resources(topic_id=q.q_int("topic_id"), subject_id=q.q_int("subject_id"),
                                           category=q.q_str("category"), difficulty=q.q_str("difficulty"),
                                           accessibility_format=q.q_str("format"), search=q.q_str("search"))),
          "List/filter learning resources", "Resources",
          query=[("topic_id", "Filter by topic"), ("subject_id", "Filter by subject"),
                 ("category", "video|notes|quiz|practice"), ("difficulty", "beginner|intermediate|advanced"),
                 ("format", "Accessibility format, e.g. captions"), ("search", "Title/description contains")])
    r.add("POST", "/api/resources", lambda q: s.create_resource(q.body), "Create a resource", "Resources",
          status=201, body=RESOURCE_BODY)
    r.add("GET", "/api/resources/{id}", lambda q: s.get_resource(q.params["id"]), "Get a resource", "Resources")
    r.add("PUT", "/api/resources/{id}", lambda q: s.update_resource(q.params["id"], q.body),
          "Update a resource", "Resources", body={"estimated_minutes": 20})
    r.add("DELETE", "/api/resources/{id}", lambda q: s.delete_resource(q.params["id"]),
          "Delete a resource", "Resources")

    # --- reports & data quality --------------------------------------------------------------
    r.add("GET", "/api/reports/class", lambda q: s.class_summary(), "Class-level summary report", "Reports")
    r.add("GET", "/api/validation-log", lambda q: items(s.list_validation_log(q.q_int("student_id"))),
          "All rejected records (data-quality log)", "Data quality", query=[("student_id", "Filter")])
    r.add("DELETE", "/api/validation-log", lambda q: s.clear_validation_log(q.q_int("student_id")),
          "Clear the log (optionally for one student)", "Data quality", query=[("student_id", "Filter")])
    r.add("DELETE", "/api/validation-log/{id}", lambda q: s.delete_validation_entry(q.params["id"]),
          "Dismiss one log entry", "Data quality")
    return r


__all__ = ["build_router", "Request"]
