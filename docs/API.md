# Learn4All REST API

Base URL (default): `http://127.0.0.1:8000`. A machine-readable spec is served at
`GET /api/openapi.json` (OpenAPI 3), and a human-readable list at `GET /api/docs`.

## Conventions

* Request and response bodies are JSON (UTF-8). Send `Content-Type: application/json`.
* CORS is enabled (`*` by default; restrict with the `LEARN4ALL_CORS` env var).
* Collections return `{"items": [...], "count": n}`.
* `PUT` and `PATCH` do **partial** updates: only the fields you send change.
* Errors always look like this:

```json
{"error": {"code": "validation_error", "message": "Validation failed",
           "details": [{"field": "score", "message": "Score 120 is greater than max score 100 (inconsistent)"}]}}
```

| Status | Meaning |
|---|---|
| 200 / 201 | OK / created |
| 400 | Malformed JSON or bad query parameter |
| 404 | Unknown record or route |
| 405 | Method not allowed on this path |
| 409 | Conflict (duplicate assessment, e-mail or code already used) |
| 422 | Validation failed: see `details` for field errors |
| 500 | Unexpected server error |

## Endpoints

### System & configuration
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/meta` | Vocabularies (categories, difficulties, assessment types, accessibility formats, statuses) + counts |
| GET | `/api/docs` | Endpoint list |
| GET | `/api/openapi.json` | OpenAPI 3 spec |
| GET | `/api/settings` | Analysis settings with spec (label, min, max, description) |
| PUT | `/api/settings` | Update settings, e.g. `{"weak_threshold": 55}` |
| POST | `/api/settings/reset` | Restore defaults |
| GET | `/api/rules` | Status rules, formulas, recommendation rules, selection policy |
| POST | `/api/admin/reset` | Erase DB and reload sample data |

### Students
| Method | Path | Description |
|---|---|---|
| GET | `/api/students?search=` | List learners with a summary (`overall_average`, `trend`, `gap_count`, `band`…) |
| POST | `/api/students` | Create |
| GET / PUT / PATCH / DELETE | `/api/students/{id}` | Read / update / delete (cascades assessments) |
| GET | `/api/students/{id}/assessments` | Learner's assessments |
| GET | `/api/students/{id}/performance` | Topic & subject indicators, trends, statuses, timeline |
| GET | `/api/students/{id}/recommendations` | Personalised plan with reasons, rule trace, exclusions |
| GET | `/api/students/{id}/report` | Full learner report (all of the above + next actions + data issues + rules) |
| GET | `/api/students/{id}/validation-log` | Rejected records for this learner |

Student body:
```json
{"name": "Asha Rao", "email": "asha@school.example", "grade_level": "Grade 8",
 "accessibility_needs": ["captions", "screen-reader"], "preferred_categories": ["video"],
 "weekly_study_minutes": 120, "notes": ""}
```

### Subjects & topics
| Method | Path | Description |
|---|---|---|
| GET | `/api/subjects?include_topics=true` | List subjects (+ topics) |
| POST | `/api/subjects` | Create, e.g. `{"code": "SCI8", "name": "Science", "topics": ["Cells", "Forces"]}` |
| GET / PUT / DELETE | `/api/subjects/{id}` | Read / update / delete (cascades) |
| GET / POST | `/api/subjects/{id}/topics` | List / add topic `{"name": "Probability"}` |
| GET | `/api/topics?subject_id=` | All topics |
| PUT / DELETE | `/api/topics/{id}` | Rename / delete |

### Assessments
| Method | Path | Description |
|---|---|---|
| GET | `/api/assessments?student_id=&subject_id=&topic_id=&from=&to=` | Filtered list |
| POST | `/api/assessments` | Create one (validated) |
| POST | `/api/assessments/bulk` | Import many: `[...]`, `{"rows": [...]}` or `{"csv": "..."}` → per-row results |
| GET / PUT / DELETE | `/api/assessments/{id}` | Read / update / delete |

Assessment body: give either ids, or references by e-mail/code/name.
```json
{"student_id": 1, "topic_id": 4, "date": "2026-10-01", "score": 36, "max_score": 50, "assessment_type": "test"}
{"student_email": "mira@learn4all.example", "subject_code": "PY101", "topic_name": "Loops",
 "date": "2026-10-01", "score": 72, "assessment_type": "quiz"}
```
Validation: required fields, numeric score `0 ≤ score ≤ max_score`, `max_score > 0`, ISO date
that is not in the future, known type (`quiz|assignment|test|exam`), existing learner/topic, topic belonging
to `subject_id` if given, and no duplicate (same learner + topic + date + type). Every rejected record is
written to the validation log.

### Resources
| Method | Path | Description |
|---|---|---|
| GET | `/api/resources?subject_id=&topic_id=&category=&difficulty=&format=&search=` | Filtered catalogue |
| POST | `/api/resources` | Create |
| GET / PUT / DELETE | `/api/resources/{id}` | Read / update / delete |

```json
{"title": "Loops Recap", "topic_id": 4, "category": "notes", "difficulty": "beginner",
 "estimated_minutes": 15, "formats": ["screen-reader", "large-print"], "url": "https://example.org/loops"}
```

### Reports & data quality
| Method | Path | Description |
|---|---|---|
| GET | `/api/reports/class` | Class summary: totals, subject/topic averages, common gaps, bands, improvers, decliners, distribution, accessibility |
| GET | `/api/validation-log?student_id=` | Rejected records |
| DELETE | `/api/validation-log?student_id=` | Clear (all or one learner) |
| DELETE | `/api/validation-log/{id}` | Dismiss one entry |

## Example: recommendation item

```json
{
  "rank": 1, "score": 12.01, "topic_name": "Loops", "gap_status": "weak", "priority_label": "high",
  "resource": {"title": "Loops Explained (Captioned)", "category": "video", "difficulty": "beginner",
               "estimated_minutes": 12, "formats": ["captions", "transcript"]},
  "summary": "Watch 'Loops Explained (Captioned)' (beginner, 12 min) because Loops is weak at 49.9%.",
  "reasons": ["'Loops' is weak — Weighted average 49.9% over 2 assessment(s) is below the 60% weak threshold…",
              "Accessible: 'captions' satisfied (captions)", "Difficulty beginner matches target beginner", "…"],
  "rule_trace": [{"rule": "R1", "allowed": true, "points": 3.51, "reason": "…"}, "…"],
  "within_weekly_budget": true
}
```

## Quick test with curl

```bash
curl http://127.0.0.1:8000/api/students
curl http://127.0.0.1:8000/api/students/1/report
curl -X POST http://127.0.0.1:8000/api/assessments -H "Content-Type: application/json" \
     -d '{"student_id":1,"topic_id":4,"date":"2026-10-01","score":120}'     # → 422
```
