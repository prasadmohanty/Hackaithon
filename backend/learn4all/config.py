"""Runtime configuration and the specification of configurable settings.

Server options can be overridden with environment variables or CLI flags
(see ``server.py``). Analysis settings are persisted in the ``settings``
table and editable through ``PUT /api/settings``.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB_PATH = os.environ.get("LEARN4ALL_DB", str(BACKEND_DIR / "data" / "learn4all.db"))
DEFAULT_HOST = os.environ.get("LEARN4ALL_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("LEARN4ALL_PORT", "8000"))
# Comma separated list of allowed origins, or "*" for any (handy in development).
CORS_ALLOWED_ORIGINS = os.environ.get("LEARN4ALL_CORS", "*")


# Every configurable analysis setting: default, type, bounds and a description
# that the API exposes so a frontend can render a settings form generically.
SETTINGS_SPEC = {
    "weak_threshold": {
        "default": 60.0, "type": "float", "min": 0, "max": 100,
        "label": "Weak-topic threshold (%)",
        "description": "A topic whose weighted average is below this value is a learning gap.",
    },
    "mastery_threshold": {
        "default": 85.0, "type": "float", "min": 0, "max": 100,
        "label": "Mastery threshold (%)",
        "description": "Weighted average at or above which a topic counts as mastered.",
    },
    "min_evidence": {
        "default": 2, "type": "int", "min": 1, "max": 10,
        "label": "Minimum evidence (assessments)",
        "description": "Assessments needed before a gap is 'confirmed' instead of 'at risk'.",
    },
    "trend_threshold": {
        "default": 3.0, "type": "float", "min": 0, "max": 50,
        "label": "Trend sensitivity (points per assessment)",
        "description": "Slope (in % points per assessment) needed to call a trend improving or declining.",
    },
    "recency_weight": {
        "default": 0.2, "type": "float", "min": 0, "max": 2,
        "label": "Recency weight",
        "description": "Extra weight given to each newer assessment (0 = all attempts equal).",
    },
    "weight_quiz": {
        "default": 1.0, "type": "float", "min": 0, "max": 10,
        "label": "Weight: quiz", "description": "Relative weight of quiz results.",
    },
    "weight_assignment": {
        "default": 1.5, "type": "float", "min": 0, "max": 10,
        "label": "Weight: assignment", "description": "Relative weight of assignment results.",
    },
    "weight_test": {
        "default": 2.0, "type": "float", "min": 0, "max": 10,
        "label": "Weight: test", "description": "Relative weight of test results.",
    },
    "weight_exam": {
        "default": 3.0, "type": "float", "min": 0, "max": 10,
        "label": "Weight: exam", "description": "Relative weight of exam results.",
    },
    "max_recommendations": {
        "default": 6, "type": "int", "min": 1, "max": 30,
        "label": "Max recommendations",
        "description": "Upper limit of resources in a learner's personalised plan.",
    },
    "max_per_topic": {
        "default": 2, "type": "int", "min": 1, "max": 10,
        "label": "Max resources per topic",
        "description": "Upper limit of resources recommended for any single topic.",
    },
}


def default_settings() -> dict:
    """Return a fresh dict of default analysis settings."""
    return {key: spec["default"] for key, spec in SETTINGS_SPEC.items()}
