"""OOP domain model for Learn4All."""

from .assessment import Assessment
from .base import ConflictError, DomainError, Entity, NotFoundError, ValidationError, field_error
from .resource import (NotesResource, PracticeResource, QuizResource, Resource,
                       TextBasedResource, VideoResource)
from .student import Person, Student
from .subject import Subject, Topic

__all__ = [
    "Assessment", "ConflictError", "DomainError", "Entity", "NotFoundError", "ValidationError",
    "field_error", "NotesResource", "PracticeResource", "QuizResource", "Resource",
    "TextBasedResource", "VideoResource", "Person", "Student", "Subject", "Topic",
]
