"""Report builders: individual learner report and class-level summary.

Both builders are pure: they receive already-computed analytics and produce
JSON-ready dicts, so they are easy to test and reuse from any interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime
from typing import Dict, List

from .analytics import StudentPerformance, mean
from .constants import TOPIC_STATUSES


class ReportBuilder(ABC):
    report_type = "report"

    def __init__(self, settings: Dict[str, float]):
        self.settings = settings

    def header(self) -> dict:
        return {"report_type": self.report_type,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "settings_used": dict(self.settings)}

    @abstractmethod
    def build(self, *args, **kwargs) -> dict:
        ...


class LearnerReportBuilder(ReportBuilder):
    report_type = "learner_report"

    def build(self, student, performance: StudentPerformance, plan: dict,
              data_issues: List[dict], rules: List[dict]) -> dict:
        report = self.header()
        report.update({
            "student": student.to_dict(),
            "summary": {
                "overall_average": performance.overall_average,
                "overall_trend": performance.overall_trend,
                "overall_slope": performance.overall_slope,
                "assessment_count": performance.assessment_count,
                "topics_assessed": len(performance.topics),
                "strength_count": len(performance.strengths),
                "gap_count": len(performance.gaps),
                "period": {"from": performance.first_date, "to": performance.last_date},
                "band": self.band(performance.overall_average),
            },
            "performance": performance.to_dict(),
            "study_plan": plan,
            "data_issues": data_issues,
            "next_actions": self.next_actions(student, performance, plan, data_issues),
            "rules_explained": {
                "status_definitions": TOPIC_STATUSES,
                "recommendation_rules": rules,
                "selection_policy": plan.get("selection_policy", []),
            },
        })
        return report

    def band(self, average) -> str:
        if average is None:
            return "no_data"
        if average >= float(self.settings["mastery_threshold"]):
            return "excelling"
        if average >= float(self.settings["weak_threshold"]):
            return "on_track"
        return "needs_support"

    def next_actions(self, student, perf: StudentPerformance, plan: dict, issues: List[dict]) -> List[dict]:
        actions = []
        if perf.assessment_count == 0:
            actions.append({"priority": "high", "action": "Record a baseline assessment for each subject "
                                                          "so gaps can be identified."})
        first_by_topic = {}
        for rec in plan.get("recommendations", []):
            first_by_topic.setdefault(rec["topic_id"], rec)
        for gap in perf.gaps[:4]:
            rec = first_by_topic.get(gap.topic_id)
            if rec:
                r = rec["resource"]
                actions.append({"priority": gap.priority_label,
                                "action": f"{r['learning_mode']} '{r['title']}' ({r['estimated_minutes']} min) "
                                          f"to work on {gap.topic_name} ({gap.weighted_average:.0f}%)."})
            if gap.count < int(self.settings["min_evidence"]):
                actions.append({"priority": "medium",
                                "action": f"Schedule another assessment in {gap.topic_name} to confirm "
                                          f"the gap (only {gap.count} result so far)."})
        for t in perf.topics:
            if t.trend == "declining":
                actions.append({"priority": "high" if t.is_gap else "medium",
                                "action": f"Review {t.topic_name}: scores are declining "
                                          f"({t.slope:+.1f} pts per assessment)."})
        for gap in plan.get("uncovered_gaps", []):
            needs = ", ".join(sorted(student.accessibility_needs)) or "the learner's level"
            actions.append({"priority": "high",
                            "action": f"Teacher: add a resource for {gap['topic_name']} that suits {needs} "
                                      f"— no eligible resource exists yet."})
        if plan.get("total_minutes", 0) > plan.get("weekly_budget_minutes", 0) > 0:
            actions.append({"priority": "low",
                            "action": f"Plan needs {plan['total_minutes']} min but weekly budget is "
                                      f"{plan['weekly_budget_minutes']} min — spread over two weeks."})
        if issues:
            actions.append({"priority": "medium",
                            "action": f"Resolve {len(issues)} rejected assessment record(s) in the "
                                      f"data-quality log."})
        for s in perf.strengths[:2]:
            if s.status == "mastered":
                actions.append({"priority": "low",
                                "action": f"Offer enrichment/advanced work in {s.topic_name} "
                                          f"({s.weighted_average:.0f}%) — topic mastered."})
        return actions


class ClassSummaryBuilder(ReportBuilder):
    report_type = "class_summary"

    def build(self, rows: List[dict], resources_count: int, issues_count: int) -> dict:
        """rows: [{"student": Student, "performance": StudentPerformance}]"""
        report = self.header()
        wt = float(self.settings["weak_threshold"])
        mt = float(self.settings["mastery_threshold"])
        topic_stats: Dict[int, dict] = {}
        subject_stats: Dict[int, dict] = {}
        students, needs = [], Counter()

        for row in rows:
            st, perf = row["student"], row["performance"]
            needs.update(st.accessibility_needs)
            for t in perf.topics:
                ts = topic_stats.setdefault(t.topic_id, {
                    "topic_id": t.topic_id, "topic_name": t.topic_name,
                    "subject_name": t.subject_name, "scores": [],
                    "weak_count": 0, "at_risk_count": 0, "mastered_count": 0, "students_weak": []})
                ts["scores"].append(t.weighted_average)
                if t.status == "weak":
                    ts["weak_count"] += 1
                if t.status == "at_risk":
                    ts["at_risk_count"] += 1
                if t.status == "mastered":
                    ts["mastered_count"] += 1
                if t.is_gap and t.status != "developing":
                    ts["students_weak"].append(st.name)
            for s in perf.subjects:
                ss = subject_stats.setdefault(s["subject_id"], {
                    "subject_id": s["subject_id"], "subject_name": s["subject_name"], "scores": []})
                ss["scores"].append(s["average"])
            band = LearnerReportBuilder(self.settings).band(perf.overall_average)
            students.append({
                "id": st.id, "name": st.name, "grade_level": st.grade_level,
                "overall_average": perf.overall_average, "trend": perf.overall_trend,
                "slope": perf.overall_slope, "assessment_count": perf.assessment_count,
                "gap_count": len(perf.gaps),
                "weak_topics": [g.topic_name for g in perf.gaps if g.status in ("weak", "at_risk")],
                "strengths": [s.topic_name for s in perf.strengths],
                "accessibility_needs": sorted(st.accessibility_needs),
                "band": band, "data_issues": row.get("issues", 0),
            })

        topics = []
        for ts in topic_stats.values():
            scores = ts.pop("scores")
            ts.update({"class_average": mean(scores), "students_assessed": len(scores)})
            topics.append(ts)
        topics.sort(key=lambda t: t["class_average"] if t["class_average"] is not None else 0)
        subjects = []
        for ss in subject_stats.values():
            scores = ss.pop("scores")
            ss.update({"class_average": mean(scores), "students_assessed": len(scores)})
            subjects.append(ss)
        subjects.sort(key=lambda s: s["subject_name"])

        averages = [s["overall_average"] for s in students if s["overall_average"] is not None]
        buckets = [("0-39", 0, 40), ("40-59", 40, 60), ("60-74", 60, 75), ("75-84", 75, 85), ("85-100", 85, 101)]
        distribution = [{"range": label, "count": sum(1 for a in averages if lo <= a < hi)}
                        for label, lo, hi in buckets]
        common = sorted((t for t in topics if t["weak_count"] + t["at_risk_count"] > 0),
                        key=lambda t: -(t["weak_count"] + t["at_risk_count"]))
        trended = [s for s in students if s["slope"] is not None]

        report.update({
            "totals": {
                "students": len(students),
                "assessments": sum(s["assessment_count"] for s in students),
                "resources": resources_count,
                "data_issues": issues_count,
                "class_average": mean(averages),
                "needs_support": sum(1 for s in students if s["band"] == "needs_support"),
                "on_track": sum(1 for s in students if s["band"] == "on_track"),
                "excelling": sum(1 for s in students if s["band"] == "excelling"),
                "with_accessibility_needs": sum(1 for s in students if s["accessibility_needs"]),
            },
            "subjects": subjects,
            "topics": topics,
            "common_weak_topics": common[:5],
            "students": sorted(students, key=lambda s: s["name"]),
            "students_needing_support": [s for s in students if s["band"] == "needs_support"
                                         or len(s["weak_topics"]) >= 2],
            "top_improvers": sorted((s for s in trended if s["slope"] > 0), key=lambda s: -s["slope"])[:3],
            "declining_students": sorted((s for s in trended if s["trend"] == "declining"),
                                         key=lambda s: s["slope"]),
            "score_distribution": distribution,
            "accessibility_needs": dict(sorted(needs.items())),
            "thresholds": {"weak": wt, "mastery": mt},
        })
        return report
