"""Person and Student entities (inheritance + composition with Assessment)."""

from __future__ import annotations

import json
import re
from typing import List, Optional

from ..constants import ACCESSIBILITY_FORMATS, RESOURCE_CATEGORIES
from .base import ConflictError, Entity, ValidationError, field_error, parse_str_set

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Person(Entity):
    """Anyone known to the system. Holds identity data and its validation."""

    role = "person"

    def __init__(self, name: str, email: Optional[str] = None, id: Optional[int] = None):
        super().__init__(id)
        self._name = (name or "").strip()
        self._email = (email or "").strip().lower() or None

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = (value or "").strip()

    @property
    def email(self) -> Optional[str]:
        return self._email

    @email.setter
    def email(self, value: Optional[str]) -> None:
        self._email = (value or "").strip().lower() or None

    def display_name(self) -> str:
        return self._name

    def validate(self) -> List[dict]:
        errors = []
        if not self._name:
            errors.append(field_error("name", "Name is required"))
        elif len(self._name) > 100:
            errors.append(field_error("name", "Name must be at most 100 characters"))
        if self._email and not EMAIL_RE.match(self._email):
            errors.append(field_error("email", "Email address is not valid"))
        return errors

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self._name, "email": self._email, "role": self.role}


class Student(Person):
    """A learner with accessibility needs, study preferences and assessment history."""

    role = "student"

    def __init__(
        self,
        name: str,
        email: Optional[str] = None,
        grade_level: str = "",
        accessibility_needs=(),
        preferred_categories=(),
        weekly_study_minutes: int = 120,
        notes: str = "",
        id: Optional[int] = None,
        created_at: Optional[str] = None,
    ):
        super().__init__(name, email, id)
        self.grade_level = (grade_level or "").strip()
        self.notes = (notes or "").strip()
        self.created_at = created_at
        self._errors: List[dict] = []
        self._accessibility_needs = parse_str_set(
            accessibility_needs, "accessibility_needs", ACCESSIBILITY_FORMATS, self._errors)
        self._preferred_categories = parse_str_set(
            preferred_categories, "preferred_categories", RESOURCE_CATEGORIES, self._errors)
        self._weekly_study_minutes = weekly_study_minutes
        self._assessments: list = []   # composition: a student owns its assessment history

    # --- encapsulated attributes ---------------------------------------
    @property
    def accessibility_needs(self) -> frozenset:
        return self._accessibility_needs

    @property
    def preferred_categories(self) -> frozenset:
        return self._preferred_categories

    @property
    def weekly_study_minutes(self) -> int:
        return self._weekly_study_minutes

    @property
    def assessments(self) -> tuple:
        """Read-only view; use add_assessment() to change the history."""
        return tuple(self._assessments)

    def has_accessibility_needs(self) -> bool:
        return bool(self._accessibility_needs)

    def add_assessment(self, assessment) -> None:
        """Add an assessment after validating it and rejecting duplicates."""
        assessment.ensure_valid()
        if self.id is not None and assessment.student_id != self.id:
            raise ValidationError([field_error("student_id", "Assessment belongs to a different student")])
        for existing in self._assessments:
            if existing.is_duplicate_of(assessment):
                raise ConflictError(
                    "Duplicate assessment: same student, topic, date and type already recorded",
                    [field_error("date", "Duplicate of assessment #%s" % existing.id)])
        self._assessments.append(assessment)

    def load_assessments(self, assessments) -> None:
        """Attach already-persisted (trusted) assessments."""
        self._assessments = list(assessments)

    # --- overriding -------------------------------------------------------
    def display_name(self) -> str:
        return f"{self.name} ({self.grade_level})" if self.grade_level else self.name

    def validate(self) -> List[dict]:
        errors = super().validate() + list(self._errors)
        minutes = self._weekly_study_minutes
        try:
            minutes = int(minutes)
            if not 0 <= minutes <= 10080:
                raise ValueError
            self._weekly_study_minutes = minutes
        except (TypeError, ValueError):
            errors.append(field_error("weekly_study_minutes", "Must be a whole number between 0 and 10080"))
        if len(self.grade_level) > 40:
            errors.append(field_error("grade_level", "Grade level must be at most 40 characters"))
        return errors

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "grade_level": self.grade_level,
            "accessibility_needs": sorted(self._accessibility_needs),
            "preferred_categories": sorted(self._preferred_categories),
            "weekly_study_minutes": self._weekly_study_minutes,
            "notes": self.notes,
            "created_at": self.created_at,
        })
        return data

    @classmethod
    def from_row(cls, row) -> "Student":
        return cls(
            name=row["name"], email=row["email"], grade_level=row["grade_level"],
            accessibility_needs=json.loads(row["accessibility_needs"] or "[]"),
            preferred_categories=json.loads(row["preferred_categories"] or "[]"),
            weekly_study_minutes=row["weekly_study_minutes"], notes=row["notes"],
            id=row["id"], created_at=row["created_at"],
        )
