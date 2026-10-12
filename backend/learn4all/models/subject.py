"""Subject and Topic entities. A Subject is composed of Topics."""

from __future__ import annotations

import re
from typing import List, Optional

from .base import Entity, ValidationError, field_error

CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,19}$")


class Topic(Entity):
    """A unit of learning inside a subject (e.g. 'Loops' in 'Python Programming')."""

    def __init__(self, subject_id: Optional[int], name: str, description: str = "",
                 id: Optional[int] = None):
        super().__init__(id)
        self.subject_id = subject_id
        self.name = (name or "").strip()
        self.description = (description or "").strip()

    def validate(self) -> List[dict]:
        errors = []
        if not self.name:
            errors.append(field_error("name", "Topic name is required"))
        elif len(self.name) > 80:
            errors.append(field_error("name", "Topic name must be at most 80 characters"))
        if not isinstance(self.subject_id, int):
            errors.append(field_error("subject_id", "A valid subject_id is required"))
        return errors

    def to_dict(self) -> dict:
        return {"id": self.id, "subject_id": self.subject_id, "name": self.name,
                "description": self.description}

    @classmethod
    def from_row(cls, row) -> "Topic":
        return cls(row["subject_id"], row["name"], row["description"], id=row["id"])


class Subject(Entity):
    """A subject of study owning an ordered collection of topics."""

    def __init__(self, code: str, name: str, description: str = "", id: Optional[int] = None):
        super().__init__(id)
        self.code = (code or "").strip().upper()
        self.name = (name or "").strip()
        self.description = (description or "").strip()
        self._topics: List[Topic] = []

    @property
    def topics(self) -> tuple:
        return tuple(self._topics)

    def add_topic(self, topic: Topic) -> Topic:
        if any(t.name.lower() == topic.name.lower() for t in self._topics):
            raise ValidationError([field_error("name", f"Topic '{topic.name}' already exists in {self.name}")])
        topic.subject_id = self.id
        self._topics.append(topic)
        return topic

    def load_topics(self, topics) -> None:
        self._topics = list(topics)

    def validate(self) -> List[dict]:
        errors = []
        if not CODE_RE.match(self.code):
            errors.append(field_error("code", "Code must be 2-20 chars: letters, digits, '-' or '_'"))
        if not self.name:
            errors.append(field_error("name", "Subject name is required"))
        elif len(self.name) > 80:
            errors.append(field_error("name", "Subject name must be at most 80 characters"))
        return errors

    def to_dict(self, include_topics: bool = False) -> dict:
        data = {"id": self.id, "code": self.code, "name": self.name, "description": self.description}
        if include_topics:
            data["topics"] = [t.to_dict() for t in self._topics]
        return data

    @classmethod
    def from_row(cls, row) -> "Subject":
        return cls(row["code"], row["name"], row["description"], id=row["id"])
