"""Assessment entity: one dated, scored attempt by a student on a topic."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from ..constants import ASSESSMENT_TYPES
from .base import Entity, ValidationError, field_error

MISSING = object()


class Assessment(Entity):
    """A validated score record. Values are kept raw until validate() is called,
    so that bad input produces precise field errors instead of crashes."""

    def __init__(self, student_id, topic_id, date, score, max_score=100,
                 assessment_type: str = "test", notes: str = "",
                 id: Optional[int] = None, created_at: Optional[str] = None):
        super().__init__(id)
        self.student_id = student_id
        self.topic_id = topic_id
        self.date = date
        self.score = score
        self.max_score = max_score
        self.assessment_type = (assessment_type or "").strip().lower()
        self.notes = (notes or "").strip()
        self.created_at = created_at

    # --- derived values ---------------------------------------------------
    @property
    def percentage(self) -> float:
        """Score normalised to 0-100 so different max scores are comparable."""
        return round(float(self.score) / float(self.max_score) * 100.0, 2)

    @property
    def date_value(self) -> date:
        return datetime.strptime(self.date, "%Y-%m-%d").date()

    def is_duplicate_of(self, other: "Assessment") -> bool:
        return (self.student_id == other.student_id and self.topic_id == other.topic_id
                and self.date == other.date and self.assessment_type == other.assessment_type
                and (self.id is None or self.id != other.id))

    # --- validation ---------------------------------------------------------
    def validate(self, today: Optional[date] = None) -> List[dict]:
        today = today or date.today()
        errors: List[dict] = []

        for field in ("student_id", "topic_id"):
            value = getattr(self, field)
            if value in (None, ""):
                errors.append(field_error(field, "This field is required"))
            else:
                try:
                    setattr(self, field, int(value))
                except (TypeError, ValueError):
                    errors.append(field_error(field, "Must be an integer id"))

        if self.date in (None, ""):
            errors.append(field_error("date", "Date is required (YYYY-MM-DD)"))
        else:
            try:
                parsed = datetime.strptime(str(self.date).strip(), "%Y-%m-%d").date()
                self.date = parsed.isoformat()
                if parsed > today:
                    errors.append(field_error("date", f"Date {self.date} is in the future"))
                elif parsed.year < 2000:
                    errors.append(field_error("date", "Date is implausibly old (before 2000)"))
            except ValueError:
                errors.append(field_error("date", f"'{self.date}' is not a valid date (use YYYY-MM-DD)"))

        max_ok = True
        try:
            self.max_score = float(self.max_score if self.max_score not in (None, "") else 100)
            if self.max_score <= 0:
                raise ValueError
        except (TypeError, ValueError):
            max_ok = False
            errors.append(field_error("max_score", "Max score must be a positive number"))

        if self.score in (None, ""):
            errors.append(field_error("score", "Score is required"))
        else:
            try:
                if isinstance(self.score, bool):
                    raise ValueError
                self.score = float(self.score)
                if self.score < 0:
                    errors.append(field_error("score", "Score cannot be negative"))
                elif max_ok and self.score > self.max_score:
                    errors.append(field_error(
                        "score", f"Score {self.score:g} is greater than max score {self.max_score:g} (inconsistent)"))
            except (TypeError, ValueError):
                errors.append(field_error("score", f"'{self.score}' is not a number"))

        if self.assessment_type not in ASSESSMENT_TYPES:
            errors.append(field_error(
                "assessment_type", f"Must be one of: {', '.join(ASSESSMENT_TYPES)}"))
        if len(self.notes) > 500:
            errors.append(field_error("notes", "Notes must be at most 500 characters"))
        return errors

    def to_dict(self) -> dict:
        data = {
            "id": self.id, "student_id": self.student_id, "topic_id": self.topic_id,
            "date": self.date, "score": self.score, "max_score": self.max_score,
            "assessment_type": self.assessment_type, "notes": self.notes,
            "created_at": self.created_at,
        }
        try:
            data["percentage"] = self.percentage
        except (TypeError, ValueError, ZeroDivisionError):
            data["percentage"] = None
        return data

    @classmethod
    def from_payload(cls, payload: dict) -> "Assessment":
        if not isinstance(payload, dict):
            raise ValidationError([field_error("body", "Assessment must be a JSON object")])
        return cls(
            student_id=payload.get("student_id"), topic_id=payload.get("topic_id"),
            date=payload.get("date"), score=payload.get("score"),
            max_score=payload.get("max_score", 100),
            assessment_type=payload.get("assessment_type") or "test",
            notes=payload.get("notes") or "",
        )

    @classmethod
    def from_row(cls, row) -> "Assessment":
        return cls(row["student_id"], row["topic_id"], row["date"], row["score"],
                   row["max_score"], row["assessment_type"], row["notes"],
                   id=row["id"], created_at=row["created_at"])
