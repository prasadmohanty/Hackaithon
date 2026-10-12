"""Explainable, rule-based recommendation engine.

Every resource is passed through a chain of polymorphic ``RecommendationRule``
objects. *Filter* rules can exclude a resource (with a reason); *scoring*
rules add points (with a reason). The final score is the gap priority plus
all rule points, so every recommendation carries a complete audit trail.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from .analytics import StudentPerformance, TopicPerformance
from .constants import DIFFICULTY_LEVELS


@dataclass
class RuleOutcome:
    rule: str
    allowed: bool
    points: float
    reason: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class RecommendationRule(ABC):
    """A single, self-describing rule."""

    code = ""
    title = ""
    kind = "scoring"          # "filter" or "scoring"
    description = ""

    def __init__(self, settings: Dict[str, float]):
        self.settings = settings

    @abstractmethod
    def evaluate(self, resource, gap: TopicPerformance, learner) -> RuleOutcome:
        """Judge one resource for one learning gap."""

    def outcome(self, allowed: bool, points: float, reason: str) -> RuleOutcome:
        return RuleOutcome(self.code, allowed, round(points, 2), reason)

    def describe(self) -> dict:
        return {"code": self.code, "title": self.title, "kind": self.kind,
                "description": self.description}


class TopicRelevanceRule(RecommendationRule):
    """Applied by the engine before the others: only gap topics qualify."""

    code, title, kind = "R1", "Topic relevance", "filter"
    description = ("Only resources for topics identified as gaps (weak, at risk or developing) are "
                   "considered. Mastered/proficient topics and topics without evidence are skipped.")

    def evaluate(self, resource, gap, learner):
        if gap is None:
            return self.outcome(False, 0, "No evidence of a gap in this topic")
        if not gap.is_gap:
            return self.outcome(False, 0, f"Topic '{gap.topic_name}' is already {gap.status} "
                                          f"({gap.weighted_average:.1f}%) — not recommended")
        return self.outcome(True, gap.priority / 10.0,
                            f"'{gap.topic_name}' is {gap.status.replace('_', ' ')} — "
                            f"{gap.explanation} (priority {gap.priority:g}, {gap.priority_label})")


class AccessibilityRule(RecommendationRule):
    code, title, kind = "R2", "Accessibility match", "filter"
    description = ("Each declared accessibility need that applies to the resource type must be "
                   "supported (e.g. captions for video, screen-reader structure for notes). "
                   "Needs that do not apply to a resource type (captions on text) are ignored.")

    def evaluate(self, resource, gap, learner):
        ok, notes = resource.accessibility_check(learner.accessibility_needs)
        if not ok:
            return self.outcome(False, 0, "Inaccessible: " + "; ".join(notes))
        points = 1.0 if learner.accessibility_needs and any("satisfied" in n for n in notes) else 0.0
        return self.outcome(True, points, "Accessible: " + "; ".join(notes))


class DifficultyFitRule(RecommendationRule):
    code, title, kind = "R3", "Difficulty fit", "filter"
    description = ("Target difficulty follows the gap: weak/at-risk below threshold -> beginner; "
                   "developing -> intermediate. Exact match +3, one level easier +1, one level "
                   "harder +0 (stretch), two levels harder is excluded as too advanced.")

    def target(self, gap: TopicPerformance) -> str:
        if gap.weighted_average < float(self.settings["weak_threshold"]) or (
                gap.latest is not None and gap.latest < float(self.settings["weak_threshold"])):
            return "beginner"
        return "intermediate"

    def evaluate(self, resource, gap, learner):
        target = self.target(gap)
        distance = DIFFICULTY_LEVELS.index(resource.difficulty) - DIFFICULTY_LEVELS.index(target)
        if distance >= 2:
            return self.outcome(False, 0, f"Too advanced: {resource.difficulty} vs target {target}")
        if distance == 0:
            return self.outcome(True, 3, f"Difficulty {resource.difficulty} matches target {target}")
        if distance == -1:
            return self.outcome(True, 1, f"Slightly easier ({resource.difficulty}) — rebuilds confidence")
        if distance == 1:
            return self.outcome(True, 0, f"One step harder ({resource.difficulty}) — stretch resource")
        return self.outcome(True, 0, f"Much easier ({resource.difficulty}) than target {target}")


class CategoryStrategyRule(RecommendationRule):
    code, title, kind = "R4", "Learning strategy", "scoring"
    description = ("Weak or at-risk topics favour concept rebuilding (notes +2, video +2, practice +1, "
                   "quiz +0.5). Developing topics favour consolidation (practice +2, quiz +2, "
                   "notes/video +0.5).")
    REBUILD = {"notes": 2, "video": 2, "practice": 1, "quiz": 0.5}
    CONSOLIDATE = {"practice": 2, "quiz": 2, "notes": 0.5, "video": 0.5}

    def evaluate(self, resource, gap, learner):
        if gap.status in ("weak", "at_risk"):
            pts = self.REBUILD.get(resource.category, 0)
            return self.outcome(True, pts, f"{resource.category.title()} suits concept rebuilding (+{pts:g})")
        pts = self.CONSOLIDATE.get(resource.category, 0)
        return self.outcome(True, pts, f"{resource.category.title()} suits consolidation (+{pts:g})")


class LearnerPreferenceRule(RecommendationRule):
    code, title, kind = "R5", "Learner preference", "scoring"
    description = "Resources in a learner's preferred categories receive +1.5."

    def evaluate(self, resource, gap, learner):
        if resource.category in learner.preferred_categories:
            return self.outcome(True, 1.5, f"Learner prefers {resource.category} (+1.5)")
        return self.outcome(True, 0, "No stated preference for this category")


class TimeEfficiencyRule(RecommendationRule):
    code, title, kind = "R6", "Time efficiency", "scoring"
    description = "Short resources are easier to fit in: <=15 min +1, <=30 min +0.5, >60 min -0.5."

    def evaluate(self, resource, gap, learner):
        m = resource.estimated_minutes
        if m <= 15:
            return self.outcome(True, 1, f"Short ({m} min) (+1)")
        if m <= 30:
            return self.outcome(True, 0.5, f"Moderate length ({m} min) (+0.5)")
        if m > 60:
            return self.outcome(True, -0.5, f"Long ({m} min) (-0.5)")
        return self.outcome(True, 0, f"{m} min")


DEFAULT_RULES = (AccessibilityRule, DifficultyFitRule, CategoryStrategyRule,
                 LearnerPreferenceRule, TimeEfficiencyRule)

SELECTION_POLICY = [
    "Gaps are processed in priority order; each gap first gets its best eligible resource.",
    "Remaining slots are filled by highest score, at most `max_per_topic` per topic and "
    "`max_recommendations` in total.",
    "Resources are marked 'within weekly budget' until the learner's weekly study minutes are used up.",
]


class RecommendationEngine:
    def __init__(self, settings: Dict[str, float], rules: Optional[List[RecommendationRule]] = None):
        self.settings = settings
        self.relevance = TopicRelevanceRule(settings)
        self.rules = rules if rules is not None else [cls(settings) for cls in DEFAULT_RULES]

    def describe_rules(self) -> List[dict]:
        return [self.relevance.describe()] + [r.describe() for r in self.rules]

    def recommend(self, learner, performance: StudentPerformance, resources: List,
                  topic_names: Optional[Dict[int, str]] = None) -> dict:
        topic_names = topic_names or {}
        perf_by_topic = {t.topic_id: t for t in performance.topics}
        candidates, excluded = [], []

        for resource in resources:
            gap = perf_by_topic.get(resource.topic_id)
            relevance = self.relevance.evaluate(resource, gap, learner)
            if not relevance.allowed:
                if gap is not None:   # explain why resources for assessed topics were skipped
                    excluded.append(self._entry(resource, gap, [relevance], topic_names))
                continue
            trace = [relevance] + [rule.evaluate(resource, gap, learner) for rule in self.rules]
            if all(o.allowed for o in trace):
                score = round(sum(o.points for o in trace), 2)
                candidates.append((score, resource, gap, trace))
            else:
                excluded.append(self._entry(resource, gap, trace, topic_names))

        selected = self._select(candidates, performance.gaps)
        budget = learner.weekly_study_minutes
        used, recommendations = 0, []
        for rank, (score, resource, gap, trace) in enumerate(selected, start=1):
            used += resource.estimated_minutes
            recommendations.append({
                "rank": rank,
                "score": score,
                "resource": resource.to_dict(),
                "topic_id": gap.topic_id,
                "topic_name": gap.topic_name,
                "subject_name": gap.subject_name,
                "gap_status": gap.status,
                "gap_priority": gap.priority,
                "priority_label": gap.priority_label,
                "within_weekly_budget": used <= budget,
                "cumulative_minutes": used,
                "reasons": [o.reason for o in trace if o.points != 0 or o.rule in ("R1", "R2")],
                "rule_trace": [o.to_dict() for o in trace],
                "summary": self._summary(resource, gap),
            })

        covered = {r["topic_id"] for r in recommendations}
        uncovered = [{"topic_id": g.topic_id, "topic_name": g.topic_name, "status": g.status,
                      "reason": "No eligible resource (none exist, or all were inaccessible/too advanced)"}
                     for g in performance.gaps if g.topic_id not in covered]

        return {
            "recommendations": recommendations,
            "excluded": excluded,
            "uncovered_gaps": uncovered,
            "total_minutes": used,
            "weekly_budget_minutes": budget,
            "rules": self.describe_rules(),
            "selection_policy": SELECTION_POLICY,
        }

    # --- helpers -------------------------------------------------------------------
    def _select(self, candidates, gaps) -> list:
        limit = int(self.settings["max_recommendations"])
        per_topic = int(self.settings["max_per_topic"])
        candidates = sorted(candidates, key=lambda c: (-c[0], c[1].estimated_minutes, c[1].id or 0))
        chosen, counts = [], {}
        for gap in gaps:                                   # pass 1: best resource per gap
            for c in candidates:
                if c[2].topic_id == gap.topic_id:
                    chosen.append(c)
                    counts[gap.topic_id] = 1
                    break
            if len(chosen) >= limit:
                break
        for c in candidates:                               # pass 2: fill remaining slots
            if len(chosen) >= limit:
                break
            if any(c[1] is x[1] for x in chosen) or counts.get(c[2].topic_id, 0) >= per_topic:
                continue
            chosen.append(c)
            counts[c[2].topic_id] = counts.get(c[2].topic_id, 0) + 1
        gap_rank = {g.topic_id: i for i, g in enumerate(gaps)}
        chosen.sort(key=lambda c: (gap_rank.get(c[2].topic_id, 99), -c[0]))
        return chosen

    @staticmethod
    def _summary(resource, gap) -> str:
        return (f"{resource.learning_mode} '{resource.title}' ({resource.difficulty}, "
                f"{resource.estimated_minutes} min) because {gap.topic_name} is "
                f"{gap.status.replace('_', ' ')} at {gap.weighted_average:.1f}%.")

    @staticmethod
    def _entry(resource, gap, trace, topic_names) -> dict:
        return {
            "resource": resource.to_dict(),
            "topic_name": gap.topic_name if gap else topic_names.get(resource.topic_id, ""),
            "reasons": [o.reason for o in trace if not o.allowed],
        }
