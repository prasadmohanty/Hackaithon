"""Base classes and errors shared by all domain entities."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional


class DomainError(Exception):
    """Base class for errors the API translates into HTTP responses."""

    status = 400
    code = "bad_request"

    def __init__(self, message: str, details: Optional[list] = None):
        super().__init__(message)
        self.message = message
        self.details = details or []

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


class ValidationError(DomainError):
    """One or more fields are missing, invalid or inconsistent."""

    status = 422
    code = "validation_error"

    def __init__(self, errors: List[dict], message: str = "Validation failed"):
        super().__init__(message, errors)
        self.errors = errors


class NotFoundError(DomainError):
    status = 404
    code = "not_found"


class ConflictError(DomainError):
    """The request clashes with existing data (e.g. a duplicate record)."""

    status = 409
    code = "conflict"


def field_error(field: str, message: str) -> dict:
    return {"field": field, "message": message}


def parse_str_set(value, field: str, allowed: Iterable[str], errors: list) -> frozenset:
    """Accept a list, a JSON list string or a comma-separated string of tokens."""
    if value is None or value == "":
        return frozenset()
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                value = json.loads(text)
            except ValueError:
                errors.append(field_error(field, "Must be a list or comma-separated text"))
                return frozenset()
        else:
            value = [part for part in text.split(",")]
    if not isinstance(value, (list, tuple, set, frozenset)):
        errors.append(field_error(field, "Must be a list or comma-separated text"))
        return frozenset()
    allowed = set(allowed)
    items = set()
    for raw in value:
        token = str(raw).strip().lower()
        if not token:
            continue
        if token not in allowed:
            errors.append(field_error(field, f"Unknown value '{token}'. Allowed: {', '.join(sorted(allowed))}"))
            continue
        items.add(token)
    return frozenset(items)


class Entity(ABC):
    """Every persisted domain object has an id, validates itself and serialises to a dict."""

    def __init__(self, id: Optional[int] = None):
        self._id = id

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        if self._id is not None and self._id != value:
            raise ValueError("Entity id cannot be changed once assigned")
        self._id = value

    @abstractmethod
    def validate(self) -> List[dict]:
        """Return a list of field errors (empty when valid)."""

    def ensure_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise ValidationError(errors)

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialise to a JSON-friendly dict."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self._id}>"
