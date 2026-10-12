# Learn4All — Inclusive Learning Progress & Resource Planner

**Hack-AI-Thon 2026 · SDG 4 (Quality Education) · SDG 10 (Reduced Inequalities)**

Learn4All tracks learner progress across subjects and topics, finds learning gaps from historical
evidence, and builds **explainable, accessibility-aware study plans** for every learner. It also
produces a class-level summary for teachers.

It has two parts that are **completely separate**:

| Part | Tech | Talks to the other via |
|------|------|------------------------|
| `backend/` – REST API | Python 3.9+ standard library only: `http.server`, `sqlite3` | JSON over HTTP |
| `frontend/` – web UI | Static HTML + CSS + vanilla JavaScript (no build step) | `fetch()` to the API |

Anyone can build a different frontend (React, mobile app, CLI…) against the API. See
[docs/API.md](docs/API.md) or open `GET /api/docs` / `GET /api/openapi.json` on a running server.

---

## Quick start

Requirements: **Python 3.9 or later**. Nothing to install: there are no third-party packages.

```bash
# 1) Start the API (creates backend/data/learn4all.db and loads sample data on first run)
cd backend
python3 server.py                 # → http://127.0.0.1:8000/api

# 2) In a second terminal, serve the frontend with Python's built-in http server
cd frontend
python3 -m http.server 5500       # → open http://127.0.0.1:5500
```

Or start both at once from the project root:

```bash
python3 run_all.py
```

### Server options

| Command | Effect |
|---------|--------|
| `python3 server.py --port 9000 --host 0.0.0.0` | Change port / bind address |
| `python3 server.py --reset` | Wipe the database and reload the sample data |
| `python3 server.py --no-seed` | Start with an empty database |
| `python3 server.py --db /path/to/file.db` | Use another SQLite file |
| `LEARN4ALL_CORS="http://localhost:5500"` | Restrict CORS (default `*`) |

If the API runs on another host or port, open the frontend with `?api=http://host:port`
(it is remembered), or change it on the **Settings** page.

### Run the tests

```bash
cd backend
python3 -m unittest discover -s tests -v
```

The suite has 27 tests. They cover the models, validation, polymorphism, analytics and the recommendation engine,
plus end-to-end HTTP tests against a temporary database.

---

## Features → requirements

| Requirement (from the brief) | Where |
|---|---|
| Student, Subject, Assessment, Resource classes with encapsulation & relationships | `backend/learn4all/models/` |
| Multiple students/subjects, history over time, validation of missing/duplicate/invalid/inconsistent entries | `models/assessment.py`, `services.py`, data-quality log |
| Subject averages, topic scores, improvement/decline rates, configurable weighted measures | `analytics.py`, Settings page |
| Weak topics from configurable thresholds + historical evidence (not one test) | `PerformanceAnalyzer.classify_status` |
| Personalised recommendations by category, difficulty, topic, accessibility | `recommender.py` |
| Resource categories video/notes/quiz/practice with difficulty, time, accessibility format | `models/resource.py` |
| Learner report + class summary (strengths, weak topics, trends, resources, next actions) | `reports.py`, learner & dashboard pages |
| Rule-based engine that explains every recommendation & avoids mastered/irrelevant topics | rules R1–R6, *Rules explained* page |
| OOP beyond basic classes (inheritance, composition, overriding, polymorphism, modules) | see [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) §5 |
| Multi-student sample incl. invalid data and accessibility needs | `seed.py` (Priya = invalid data; Mira, Arjun, Sara, Kabir, Dev = accessibility) |

## Sample data (fictional)

| Learner | Scenario |
|---|---|
| Mira Sharma | Needs **captions**; weak in Loops (45, 52 → avg 48.5) like the sample solution; uncaptioned video filtered out |
| Arjun Mehta | **Screen-reader + large print**; weak Geometry, only audio-described/screen-reader resources offered |
| Sara Khan | **Dyslexia-friendly**; weak Grammar, improving Reading |
| Leo Fernandes | High performer, mostly mastered → enrichment suggestions |
| Priya Nair | **8 invalid records**: score > max, missing date, non-numeric, future date, duplicate, unknown topic, bad type, negative |
| Kabir Singh | **Sign language + captions**; strongly improving Algebra |
| Zoya Ali | **Declining** Functions / OOP scores |
| Dev Patel | **Transcript**; prefers practice & quizzes |

## Project structure

```
learn4all/
├── run_all.py                  # optional launcher for both servers
├── backend/
│   ├── server.py               # API entry point (http.server)
│   ├── data/                   # SQLite database (created at runtime)
│   ├── learn4all/
│   │   ├── models/             # OOP domain model
│   │   │   ├── base.py         #   Entity (abstract), errors, helpers
│   │   │   ├── student.py      #   Person → Student
│   │   │   ├── subject.py      #   Subject ◇ Topic
│   │   │   ├── assessment.py   #   Assessment (validation)
│   │   │   └── resource.py     #   Resource → Video / TextBased → Notes, Quiz, Practice
│   │   ├── database.py         # schema + repositories
│   │   ├── analytics.py        # performance indicators, trends, gap detection
│   │   ├── recommender.py      # explainable rule engine (R1–R6)
│   │   ├── reports.py          # learner report & class summary builders
│   │   ├── services.py         # use-cases (used by the API)
│   │   ├── seed.py             # sample data
│   │   ├── config.py, constants.py
│   │   └── api/                # router, endpoint table, HTTP handler
│   └── tests/test_learn4all.py
├── frontend/                   # independent static web client
│   ├── index.html
│   ├── css/styles.css
│   └── js/ (config, api client, ui kit, charts, views/)
└── docs/
    ├── API.md
    └── PROJECT_REPORT.md
```

## External libraries

None. The backend uses only the Python standard library. The frontend uses only browser APIs: charts are hand-drawn SVG, and there are no CDNs, so it works offline.
