"""SQLite persistence: schema management and one repository per aggregate.

Repositories only translate between rows and domain objects; business rules
live in the models, analytics and services modules.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .config import SETTINGS_SPEC, default_settings
from .models import Assessment, Resource, Student, Subject, Topic

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    email                TEXT UNIQUE,
    grade_level          TEXT NOT NULL DEFAULT '',
    accessibility_needs  TEXT NOT NULL DEFAULT '[]',
    preferred_categories TEXT NOT NULL DEFAULT '[]',
    weekly_study_minutes INTEGER NOT NULL DEFAULT 120,
    notes                TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    UNIQUE (subject_id, name)
);
CREATE TABLE IF NOT EXISTS assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    topic_id        INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    date            TEXT NOT NULL,
    score           REAL NOT NULL,
    max_score       REAL NOT NULL DEFAULT 100,
    assessment_type TEXT NOT NULL DEFAULT 'test',
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (student_id, topic_id, date, assessment_type)
);
CREATE INDEX IF NOT EXISTS idx_assessments_student ON assessments(student_id);
CREATE TABLE IF NOT EXISTS resources (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    topic_id          INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    category          TEXT NOT NULL,
    difficulty        TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL,
    formats           TEXT NOT NULL DEFAULT '[]',
    url               TEXT NOT NULL DEFAULT '',
    description       TEXT NOT NULL DEFAULT '',
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS validation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    source     TEXT NOT NULL,
    payload    TEXT NOT NULL,
    errors     TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

TABLES = ("validation_log", "assessments", "resources", "topics", "subjects", "students", "settings")


class Database:
    """Opens short-lived connections (safe for the threaded HTTP server)."""

    def __init__(self, path: str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def drop_all(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            for table in TABLES:
                conn.execute(f"DROP TABLE IF EXISTS {table}")

    def is_empty(self) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0


class Repository:
    """Common helpers for table-backed repositories."""

    table = ""
    entity = None

    def __init__(self, db: Database):
        self.db = db

    def _to_entity(self, row):
        return self.entity.from_row(row)

    def get(self, entity_id: int):
        with self.db.connect() as conn:
            row = conn.execute(f"SELECT * FROM {self.table} WHERE id = ?", (entity_id,)).fetchone()
        return self._to_entity(row) if row else None

    def delete(self, entity_id: int) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (entity_id,))
        return cur.rowcount > 0

    def count(self) -> int:
        with self.db.connect() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()[0]

    def _query(self, sql: str, params=()) -> list:
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._to_entity(r) for r in rows]


class StudentRepository(Repository):
    table, entity = "students", Student

    def list(self, search: Optional[str] = None) -> List[Student]:
        if search:
            like = f"%{search.strip()}%"
            return self._query("SELECT * FROM students WHERE name LIKE ? OR email LIKE ? ORDER BY name",
                               (like, like))
        return self._query("SELECT * FROM students ORDER BY name")

    def find_by_email(self, email: str) -> Optional[Student]:
        found = self._query("SELECT * FROM students WHERE email = ?", ((email or "").lower(),))
        return found[0] if found else None

    def _values(self, s: Student) -> tuple:
        return (s.name, s.email, s.grade_level, json.dumps(sorted(s.accessibility_needs)),
                json.dumps(sorted(s.preferred_categories)), s.weekly_study_minutes, s.notes)

    def add(self, s: Student) -> Student:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO students (name, email, grade_level, accessibility_needs, "
                "preferred_categories, weekly_study_minutes, notes) VALUES (?,?,?,?,?,?,?)",
                self._values(s))
        return self.get(cur.lastrowid)

    def update(self, s: Student) -> Student:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE students SET name=?, email=?, grade_level=?, accessibility_needs=?, "
                "preferred_categories=?, weekly_study_minutes=?, notes=? WHERE id=?",
                self._values(s) + (s.id,))
        return self.get(s.id)


class SubjectRepository(Repository):
    table, entity = "subjects", Subject

    def list(self) -> List[Subject]:
        return self._query("SELECT * FROM subjects ORDER BY name")

    def find_by_code(self, code: str) -> Optional[Subject]:
        found = self._query("SELECT * FROM subjects WHERE code = ?", ((code or "").upper(),))
        return found[0] if found else None

    def add(self, s: Subject) -> Subject:
        with self.db.connect() as conn:
            cur = conn.execute("INSERT INTO subjects (code, name, description) VALUES (?,?,?)",
                               (s.code, s.name, s.description))
        return self.get(cur.lastrowid)

    def update(self, s: Subject) -> Subject:
        with self.db.connect() as conn:
            conn.execute("UPDATE subjects SET code=?, name=?, description=? WHERE id=?",
                         (s.code, s.name, s.description, s.id))
        return self.get(s.id)


class TopicRepository(Repository):
    table, entity = "topics", Topic

    def list(self, subject_id: Optional[int] = None) -> List[Topic]:
        if subject_id is not None:
            return self._query("SELECT * FROM topics WHERE subject_id = ? ORDER BY id", (subject_id,))
        return self._query("SELECT * FROM topics ORDER BY subject_id, id")

    def find(self, subject_id: int, name: str) -> Optional[Topic]:
        found = self._query("SELECT * FROM topics WHERE subject_id = ? AND lower(name) = lower(?)",
                            (subject_id, (name or "").strip()))
        return found[0] if found else None

    def add(self, t: Topic) -> Topic:
        with self.db.connect() as conn:
            cur = conn.execute("INSERT INTO topics (subject_id, name, description) VALUES (?,?,?)",
                               (t.subject_id, t.name, t.description))
        return self.get(cur.lastrowid)

    def update(self, t: Topic) -> Topic:
        with self.db.connect() as conn:
            conn.execute("UPDATE topics SET subject_id=?, name=?, description=? WHERE id=?",
                         (t.subject_id, t.name, t.description, t.id))
        return self.get(t.id)


class AssessmentRepository(Repository):
    table, entity = "assessments", Assessment

    def list(self, student_id: Optional[int] = None, topic_id: Optional[int] = None,
             subject_id: Optional[int] = None, date_from: Optional[str] = None,
             date_to: Optional[str] = None) -> List[Assessment]:
        sql = "SELECT a.* FROM assessments a JOIN topics t ON t.id = a.topic_id WHERE 1=1"
        params: list = []
        for clause, value in (("a.student_id = ?", student_id), ("a.topic_id = ?", topic_id),
                              ("t.subject_id = ?", subject_id), ("a.date >= ?", date_from),
                              ("a.date <= ?", date_to)):
            if value is not None:
                sql += f" AND {clause}"
                params.append(value)
        return self._query(sql + " ORDER BY a.date, a.id", params)

    def find_duplicate(self, a: Assessment) -> Optional[Assessment]:
        found = self._query(
            "SELECT * FROM assessments WHERE student_id=? AND topic_id=? AND date=? "
            "AND assessment_type=? AND id IS NOT ?",
            (a.student_id, a.topic_id, a.date, a.assessment_type, a.id))
        return found[0] if found else None

    def add(self, a: Assessment) -> Assessment:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO assessments (student_id, topic_id, date, score, max_score, "
                "assessment_type, notes) VALUES (?,?,?,?,?,?,?)",
                (a.student_id, a.topic_id, a.date, a.score, a.max_score, a.assessment_type, a.notes))
        return self.get(cur.lastrowid)

    def update(self, a: Assessment) -> Assessment:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE assessments SET student_id=?, topic_id=?, date=?, score=?, max_score=?, "
                "assessment_type=?, notes=? WHERE id=?",
                (a.student_id, a.topic_id, a.date, a.score, a.max_score, a.assessment_type,
                 a.notes, a.id))
        return self.get(a.id)


class ResourceRepository(Repository):
    table, entity = "resources", Resource

    def list(self, topic_id: Optional[int] = None, subject_id: Optional[int] = None,
             category: Optional[str] = None, difficulty: Optional[str] = None,
             accessibility_format: Optional[str] = None, search: Optional[str] = None) -> List[Resource]:
        sql = "SELECT r.* FROM resources r JOIN topics t ON t.id = r.topic_id WHERE 1=1"
        params: list = []
        for clause, value in (("r.topic_id = ?", topic_id), ("t.subject_id = ?", subject_id),
                              ("r.category = ?", category), ("r.difficulty = ?", difficulty)):
            if value is not None:
                sql += f" AND {clause}"
                params.append(value)
        if accessibility_format:
            sql += " AND EXISTS (SELECT 1 FROM json_each(r.formats) WHERE value = ?)"
            params.append(accessibility_format)
        if search:
            sql += " AND (r.title LIKE ? OR r.description LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        return self._query(sql + " ORDER BY t.subject_id, r.topic_id, r.difficulty, r.title", params)

    def _values(self, r: Resource) -> tuple:
        return (r.title, r.topic_id, r.category, r.difficulty, r.estimated_minutes,
                json.dumps(sorted(r.formats)), r.url, r.description)

    def add(self, r: Resource) -> Resource:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO resources (title, topic_id, category, difficulty, estimated_minutes, "
                "formats, url, description) VALUES (?,?,?,?,?,?,?,?)", self._values(r))
        return self.get(cur.lastrowid)

    def update(self, r: Resource) -> Resource:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE resources SET title=?, topic_id=?, category=?, difficulty=?, "
                "estimated_minutes=?, formats=?, url=?, description=? WHERE id=?",
                self._values(r) + (r.id,))
        return self.get(r.id)


class SettingsRepository:
    """Key/value store for analysis settings; missing keys fall back to defaults."""

    def __init__(self, db: Database):
        self.db = db

    def get_all(self) -> Dict[str, float]:
        values = default_settings()
        with self.db.connect() as conn:
            for row in conn.execute("SELECT key, value FROM settings"):
                if row["key"] in SETTINGS_SPEC:
                    values[row["key"]] = json.loads(row["value"])
        return values

    def save(self, values: Dict[str, float]) -> None:
        with self.db.connect() as conn:
            for key, value in values.items():
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                             (key, json.dumps(value)))

    def reset(self) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM settings")


class ValidationLogRepository:
    """Audit trail of rejected input (missing, invalid, duplicate, inconsistent)."""

    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _row(row) -> dict:
        return {"id": row["id"], "student_id": row["student_id"], "source": row["source"],
                "payload": json.loads(row["payload"]), "errors": json.loads(row["errors"]),
                "created_at": row["created_at"]}

    def add(self, source: str, payload, errors: list, student_id: Optional[int] = None) -> dict:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO validation_log (student_id, source, payload, errors) VALUES (?,?,?,?)",
                (student_id, source, json.dumps(payload, default=str), json.dumps(errors)))
            row = conn.execute("SELECT * FROM validation_log WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._row(row)

    def list(self, student_id: Optional[int] = None) -> List[dict]:
        with self.db.connect() as conn:
            if student_id is not None:
                rows = conn.execute("SELECT * FROM validation_log WHERE student_id = ? ORDER BY id DESC",
                                    (student_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM validation_log ORDER BY id DESC").fetchall()
        return [self._row(r) for r in rows]

    def delete(self, entry_id: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM validation_log WHERE id = ?", (entry_id,)).rowcount > 0

    def clear(self, student_id: Optional[int] = None) -> int:
        with self.db.connect() as conn:
            if student_id is not None:
                return conn.execute("DELETE FROM validation_log WHERE student_id = ?", (student_id,)).rowcount
            return conn.execute("DELETE FROM validation_log").rowcount
