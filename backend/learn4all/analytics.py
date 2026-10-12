"""Performance analytics: averages, weighted measures, trends and gap detection.

Algorithms
----------
* Percentage      score / max_score * 100, so different scales are comparable.
* Weighted avg    sum(w_i * p_i) / sum(w_i), where
                  w_i = type_weight(assessment_type) * (1 + recency_weight * i)
                  and i is the chronological index (0 = oldest attempt).
* Trend slope     least-squares slope of percentage vs attempt index
                  (percentage points gained/lost per assessment).
* Improvement     (latest - first) / first * 100 (%).
* Status          rule table using weak/mastery thresholds, the amount of
                  historical evidence and the trend (see classify_status).
* Priority        how urgently a gap needs attention:
                  (mastery - weighted_avg) * severity + decline bonus.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .constants import GAP_STATUSES, STRENGTH_STATUSES


def mean(values: Iterable[float]) -> Optional[float]:
    values = list(values)
    return round(sum(values) / len(values), 2) if values else None


def slope(values: List[float]) -> Optional[float]:
    """Least-squares slope of values against their index."""
    n = len(values)
    if n < 2:
        return None
    mx, my = (n - 1) / 2.0, sum(values) / n
    den = sum((x - mx) ** 2 for x in range(n))
    return round(sum((x - mx) * (y - my) for x, y in enumerate(values)) / den, 2)


@dataclass
class ScorePoint:
    assessment_id: int
    date: str
    percentage: float
    assessment_type: str
    weight: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class TopicPerformance:
    topic_id: int
    topic_name: str
    subject_id: int
    subject_name: str
    points: List[ScorePoint] = field(default_factory=list)
    average: Optional[float] = None
    weighted_average: Optional[float] = None
    latest: Optional[float] = None
    first: Optional[float] = None
    best: Optional[float] = None
    lowest: Optional[float] = None
    change: Optional[float] = None
    improvement_rate: Optional[float] = None
    slope: Optional[float] = None
    trend: str = "insufficient_data"
    status: str = "no_data"
    evidence: str = "none"
    priority: float = 0.0
    priority_label: str = "none"
    explanation: str = ""

    @property
    def count(self) -> int:
        return len(self.points)

    @property
    def is_gap(self) -> bool:
        return self.status in GAP_STATUSES

    @property
    def is_strength(self) -> bool:
        return self.status in STRENGTH_STATUSES

    def to_dict(self, include_points: bool = True) -> dict:
        data = {k: v for k, v in self.__dict__.items() if k != "points"}
        data["count"] = self.count
        if include_points:
            data["history"] = [p.to_dict() for p in self.points]
        return data


@dataclass
class StudentPerformance:
    topics: List[TopicPerformance]
    subjects: List[dict]
    overall_average: Optional[float]
    overall_trend: str
    overall_slope: Optional[float]
    assessment_count: int
    timeline: List[dict]
    first_date: Optional[str]
    last_date: Optional[str]

    @property
    def gaps(self) -> List[TopicPerformance]:
        return sorted((t for t in self.topics if t.is_gap), key=lambda t: -t.priority)

    @property
    def strengths(self) -> List[TopicPerformance]:
        return sorted((t for t in self.topics if t.is_strength), key=lambda t: -(t.weighted_average or 0))

    def to_dict(self) -> dict:
        return {
            "overall_average": self.overall_average,
            "overall_trend": self.overall_trend,
            "overall_slope": self.overall_slope,
            "assessment_count": self.assessment_count,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "subjects": self.subjects,
            "topics": [t.to_dict() for t in self.topics],
            "strengths": [t.to_dict(False) for t in self.strengths],
            "weak_topics": [t.to_dict(False) for t in self.gaps],
            "timeline": self.timeline,
        }


class PerformanceAnalyzer:
    """Computes performance indicators for one learner from validated assessments."""

    def __init__(self, settings: Dict[str, float]):
        self.settings = settings

    # --- configuration helpers ---------------------------------------------------
    @property
    def weak_threshold(self) -> float:
        return float(self.settings["weak_threshold"])

    @property
    def mastery_threshold(self) -> float:
        return float(self.settings["mastery_threshold"])

    @property
    def min_evidence(self) -> int:
        return int(self.settings["min_evidence"])

    def type_weight(self, assessment_type: str) -> float:
        return float(self.settings.get(f"weight_{assessment_type}", 1.0))

    # --- core calculations ---------------------------------------------------------
    def weighted_average(self, points: List[ScorePoint]) -> Optional[float]:
        total = sum(p.weight for p in points)
        if not points:
            return None
        if total <= 0:
            return mean(p.percentage for p in points)
        return round(sum(p.weight * p.percentage for p in points) / total, 2)

    def classify_trend(self, slope_value: Optional[float]) -> str:
        if slope_value is None:
            return "insufficient_data"
        threshold = float(self.settings["trend_threshold"])
        if slope_value >= threshold:
            return "improving"
        if slope_value <= -threshold:
            return "declining"
        return "stable"

    def classify_status(self, tp: TopicPerformance) -> str:
        """Rule table that uses historical evidence, not just one assessment."""
        if tp.count == 0:
            return "no_data"
        limited = tp.count < self.min_evidence
        wavg, wt, mt = tp.weighted_average, self.weak_threshold, self.mastery_threshold
        if wavg < wt:
            return "at_risk" if limited else "weak"
        if tp.trend == "declining" and tp.latest < wt:
            return "at_risk"
        if wavg >= mt:
            return "proficient" if (limited or tp.trend == "declining") else "mastered"
        if wavg < (wt + mt) / 2:
            return "developing"
        return "proficient"

    def explain(self, tp: TopicPerformance) -> str:
        wt, mt = self.weak_threshold, self.mastery_threshold
        if tp.status == "no_data":
            return "No valid assessments yet."
        base = f"Weighted average {tp.weighted_average:.1f}% over {tp.count} assessment(s)"
        reasons = {
            "weak": f"{base} is below the {wt:g}% weak threshold, confirmed by {tp.count} results.",
            "at_risk": (f"{base} with latest {tp.latest:.1f}% — below {wt:g}% but only "
                        f"{tp.count} result(s) (need {self.min_evidence} to confirm)."
                        if tp.count < self.min_evidence else
                        f"{base}; declining trend ({tp.slope:+.1f} pts/assessment) and latest "
                        f"{tp.latest:.1f}% is below {wt:g}%."),
            "developing": f"{base} is above {wt:g}% but well below mastery ({mt:g}%).",
            "proficient": f"{base} — solid, approaching or at {mt:g}% mastery.",
            "mastered": f"{base} is at/above the {mt:g}% mastery threshold with a non-declining trend.",
        }
        return reasons[tp.status]

    def prioritise(self, tp: TopicPerformance) -> None:
        if not tp.is_gap:
            tp.priority, tp.priority_label = 0.0, "none"
            return
        severity = {"weak": 1.0, "at_risk": 0.8, "developing": 0.5}[tp.status]
        gap = max(0.0, self.mastery_threshold - tp.weighted_average)
        bonus = 10.0 if tp.trend == "declining" else 0.0
        tp.priority = round(gap * severity + bonus, 1)
        tp.priority_label = "high" if tp.priority >= 35 else "medium" if tp.priority >= 20 else "low"

    def analyse_topic(self, topic, subject, assessments: List) -> TopicPerformance:
        ordered = sorted(assessments, key=lambda a: (a.date, a.id or 0))
        recency = float(self.settings["recency_weight"])
        tp = TopicPerformance(topic.id, topic.name, subject.id, subject.name)
        tp.points = [
            ScorePoint(a.id, a.date, a.percentage, a.assessment_type,
                       round(self.type_weight(a.assessment_type) * (1 + recency * i), 3))
            for i, a in enumerate(ordered)
        ]
        if tp.points:
            pcts = [p.percentage for p in tp.points]
            tp.average = mean(pcts)
            tp.weighted_average = self.weighted_average(tp.points)
            tp.first, tp.latest = pcts[0], pcts[-1]
            tp.best, tp.lowest = max(pcts), min(pcts)
            if len(pcts) > 1:
                tp.change = round(tp.latest - tp.first, 2)
                tp.improvement_rate = round(tp.change / tp.first * 100, 1) if tp.first else None
            tp.slope = slope(pcts)
            tp.trend = self.classify_trend(tp.slope)
            tp.evidence = "confirmed" if len(pcts) >= self.min_evidence else "limited"
        tp.status = self.classify_status(tp)
        tp.explanation = self.explain(tp)
        self.prioritise(tp)
        return tp

    def analyse_student(self, assessments: List, topics_by_id: Dict[int, object],
                        subjects_by_id: Dict[int, object]) -> StudentPerformance:
        by_topic: Dict[int, list] = defaultdict(list)
        for a in assessments:
            by_topic[a.topic_id].append(a)

        topics = []
        for topic_id, items in by_topic.items():
            topic = topics_by_id.get(topic_id)
            if topic is None:
                continue
            topics.append(self.analyse_topic(topic, subjects_by_id[topic.subject_id], items))
        topics.sort(key=lambda t: (t.subject_name, t.topic_name))

        subjects = []
        for subject_id in sorted({t.subject_id for t in topics}):
            sub_topics = [t for t in topics if t.subject_id == subject_id]
            chronological = sorted((p for t in sub_topics for p in t.points), key=lambda p: p.date)
            sub_slope = slope([p.percentage for p in chronological])
            subjects.append({
                "subject_id": subject_id,
                "subject_name": subjects_by_id[subject_id].name,
                "average": mean(t.weighted_average for t in sub_topics),
                "simple_average": mean(p.percentage for p in chronological),
                "topic_count": len(sub_topics),
                "assessment_count": len(chronological),
                "weak_count": sum(1 for t in sub_topics if t.is_gap),
                "slope": sub_slope,
                "trend": self.classify_trend(sub_slope),
            })

        by_date: Dict[str, list] = defaultdict(list)
        for t in topics:
            for p in t.points:
                by_date[p.date].append(p.percentage)
        timeline = [{"date": d, "average": mean(v), "count": len(v)} for d, v in sorted(by_date.items())]
        overall_slope = slope([row["average"] for row in timeline])

        return StudentPerformance(
            topics=topics,
            subjects=subjects,
            overall_average=mean(s["average"] for s in subjects),
            overall_trend=self.classify_trend(overall_slope),
            overall_slope=overall_slope,
            assessment_count=sum(t.count for t in topics),
            timeline=timeline,
            first_date=timeline[0]["date"] if timeline else None,
            last_date=timeline[-1]["date"] if timeline else None,
        )
