"""Learning resources: an abstract base with polymorphic subclasses per category.

Each subclass decides how a learner's accessibility need applies to it via
``requirement_for(need)``. For example "captions" matters for a video but is
not applicable to text notes, while "screen-reader" on a video can be met by
an audio description or a transcript.
"""

from __future__ import annotations

import json
from abc import abstractmethod
from typing import Dict, List, Optional, Tuple, Type

from ..constants import ACCESSIBILITY_FORMATS, DIFFICULTY_LEVELS, RESOURCE_CATEGORIES
from .base import Entity, ValidationError, field_error, parse_str_set


class Resource(Entity):
    """Abstract learning resource. Concrete categories register themselves."""

    category: Optional[str] = None
    learning_mode = "Study"
    _registry: Dict[str, Type["Resource"]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.category:
            Resource._registry[cls.category] = cls

    def __init__(self, title: str, topic_id, difficulty: str, estimated_minutes,
                 formats=(), url: str = "", description: str = "",
                 id: Optional[int] = None, created_at: Optional[str] = None):
        super().__init__(id)
        self.title = (title or "").strip()
        self.topic_id = topic_id
        self.difficulty = (difficulty or "").strip().lower()
        self.estimated_minutes = estimated_minutes
        self.url = (url or "").strip()
        self.description = (description or "").strip()
        self.created_at = created_at
        self._errors: List[dict] = []
        self._formats = parse_str_set(formats, "formats", ACCESSIBILITY_FORMATS, self._errors)

    @property
    def formats(self) -> frozenset:
        return self._formats

    # --- polymorphic behaviour --------------------------------------------
    @abstractmethod
    def requirement_for(self, need: str) -> Optional[frozenset]:
        """Formats that satisfy `need` for this kind of resource, or None if N/A."""

    def accessibility_check(self, needs) -> Tuple[bool, List[str]]:
        """Return (accessible?, explanations) for a learner's set of needs."""
        if not needs:
            return True, ["No accessibility needs declared"]
        ok, notes = True, []
        for need in sorted(needs):
            acceptable = self.requirement_for(need)
            if acceptable is None:
                notes.append(f"'{need}' not applicable to a {self.category} resource")
            elif self._formats & acceptable:
                notes.append(f"'{need}' satisfied ({', '.join(sorted(self._formats & acceptable))})")
            else:
                ok = False
                notes.append(f"'{need}' NOT supported (needs one of: {', '.join(sorted(acceptable))})")
        return ok, notes

    # --- validation & serialisation ------------------------------------------
    def validate(self) -> List[dict]:
        errors = list(self._errors)
        if not self.title:
            errors.append(field_error("title", "Title is required"))
        elif len(self.title) > 150:
            errors.append(field_error("title", "Title must be at most 150 characters"))
        try:
            self.topic_id = int(self.topic_id)
        except (TypeError, ValueError):
            errors.append(field_error("topic_id", "A valid topic_id is required"))
        if self.difficulty not in DIFFICULTY_LEVELS:
            errors.append(field_error("difficulty", f"Must be one of: {', '.join(DIFFICULTY_LEVELS)}"))
        try:
            minutes = int(self.estimated_minutes)
            if not 1 <= minutes <= 600:
                raise ValueError
            self.estimated_minutes = minutes
        except (TypeError, ValueError):
            errors.append(field_error("estimated_minutes", "Must be a whole number of minutes (1-600)"))
        if self.url and not self.url.startswith(("http://", "https://")):
            errors.append(field_error("url", "URL must start with http:// or https://"))
        return errors

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "topic_id": self.topic_id,
            "category": self.category, "learning_mode": self.learning_mode,
            "difficulty": self.difficulty, "estimated_minutes": self.estimated_minutes,
            "formats": sorted(self._formats), "url": self.url,
            "description": self.description, "created_at": self.created_at,
        }

    # --- factory ------------------------------------------------------------------
    @classmethod
    def create(cls, category: str, **kwargs) -> "Resource":
        key = (category or "").strip().lower()
        if key not in cls._registry:
            raise ValidationError([field_error(
                "category", f"Must be one of: {', '.join(RESOURCE_CATEGORIES)}")])
        return cls._registry[key](**kwargs)

    @classmethod
    def from_row(cls, row) -> "Resource":
        return cls.create(
            row["category"], title=row["title"], topic_id=row["topic_id"],
            difficulty=row["difficulty"], estimated_minutes=row["estimated_minutes"],
            formats=json.loads(row["formats"] or "[]"), url=row["url"],
            description=row["description"], id=row["id"], created_at=row["created_at"])


class VideoResource(Resource):
    category = "video"
    learning_mode = "Watch"
    _REQUIREMENTS = {
        "captions": frozenset({"captions"}),
        "transcript": frozenset({"transcript"}),
        "audio-description": frozenset({"audio-description"}),
        "sign-language": frozenset({"sign-language"}),
        "screen-reader": frozenset({"audio-description", "transcript"}),
    }

    def requirement_for(self, need):
        return self._REQUIREMENTS.get(need)


class TextBasedResource(Resource):
    """Shared accessibility rules for text-first resources (no category of its own)."""

    _REQUIREMENTS = {
        "screen-reader": frozenset({"screen-reader"}),
        "large-print": frozenset({"large-print"}),
        "dyslexia-friendly": frozenset({"dyslexia-friendly"}),
    }

    def requirement_for(self, need):
        return self._REQUIREMENTS.get(need)


class NotesResource(TextBasedResource):
    category = "notes"
    learning_mode = "Read"


class QuizResource(TextBasedResource):
    category = "quiz"
    learning_mode = "Self-test"


class PracticeResource(TextBasedResource):
    category = "practice"
    learning_mode = "Hands-on practice"

    def requirement_for(self, need):
        # Practice tasks are interactive; a transcript of instructions also helps
        # screen-reader users, so accept either format.
        if need == "screen-reader":
            return frozenset({"screen-reader", "transcript"})
        return super().requirement_for(need)
