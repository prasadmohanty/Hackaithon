"""Learn4All - Inclusive Learning Progress & Resource Planner.

A standard-library-only Python backend (http.server + sqlite3) exposing a
JSON REST API. Any frontend can be built on top of the API.

Package layout
--------------
constants.py     Domain vocabularies (categories, difficulties, formats ...)
config.py        Runtime configuration and configurable analysis settings
models/          OOP domain model (Student, Subject, Topic, Assessment, Resource)
database.py      SQLite schema + repository classes (persistence only)
analytics.py     Performance indicators, trends and weak-topic detection
recommender.py   Explainable rule-based recommendation engine
reports.py       Individual learner report and class-level summary
services.py      Application service (use-cases) used by the API layer
seed.py          Representative multi-student sample data
api/             Router, HTTP handler and endpoint definitions
"""

__version__ = "1.0.0"
