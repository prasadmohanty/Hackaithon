# Learn4All — Project Report

**Hack-AI-Thon 2026 · National Level Group Project**
Theme: Python Fundamentals + Object-Oriented Programming + Sustainable Development Goals

## 1. Problem statement

Teachers rarely have time to dig through every learner's assessment history, work out which topics are
real gaps (and which are one-off bad days), and then find study material that the learner can actually use.
Learners with disabilities are often given resources they cannot access: a video without captions,
or notes that do not work with a screen reader. The result is uneven support and widening inequality.

## 2. SDG mapping

| SDG | How Learn4All contributes |
|---|---|
| **SDG 4 – Quality Education** (target 4.1, 4.5) | Evidence-based identification of learning gaps; personalised, explainable study plans; class-level insight for teachers |
| **SDG 10 – Reduced Inequalities** (target 10.2) | Accessibility needs are first-class data; resources that a learner cannot access are never recommended; gaps with no accessible resource are flagged to the teacher |

## 3. Objectives

1. Track multiple learners, subjects, topics and dated assessments, with robust validation.
2. Compute subject/topic averages, configurable weighted measures and improvement/decline trends.
3. Identify weak topics from configurable thresholds and **historical evidence**.
4. Recommend resources matched on topic, difficulty, category and **accessibility**.
5. Explain every decision (rules, formulas, rule trace, exclusions).
6. Produce an individual learner report and a class summary.
7. Expose everything as a modular REST API, so any frontend can be built on it.

## 4. System design

```
 ┌───────────────────────┐   HTTP + JSON  ┌──────────────────────────────────────────────┐
 │ Frontend (separate)   │ ─────────────▶ │ api/ (http.server, Router, routes)           │
 │ HTML/CSS/JS, fetch()  │ ◀───────────── │   └─▶ services.py  (use-cases)               │
 └───────────────────────┘                │         ├─▶ models/       validation, OOP    │
                                          │         ├─▶ analytics.py  indicators, status │
   any other client (mobile, CLI, BI…)    │         ├─▶ recommender.py rules R1–R6       │
                                          │         ├─▶ reports.py     report builders   │
                                          │         └─▶ database.py    repositories      │
                                          │                  └─▶ SQLite (learn4all.db)   │
                                          └──────────────────────────────────────────────┘
```

* **Layered architecture**: HTTP → service → domain/analytics → repository → SQLite. Each layer only
  talks to the one below it.
* **Persistence**: SQLite with foreign keys and `ON DELETE CASCADE`, a `UNIQUE` constraint against duplicate
  assessments, a `settings` table for configurable thresholds and a `validation_log` table recording rejected input.
* **API**: a small regex router that documents itself (it generates `/api/docs` and the OpenAPI spec), uses
  consistent error envelopes and supports CORS.

### Database tables
`students`, `subjects`, `topics`, `assessments`, `resources`, `settings`, `validation_log`.

## 5. Classes and OOP concepts

| Class | Responsibility | OOP concept |
|---|---|---|
| `Entity` (abstract) | id, `validate()`, `ensure_valid()`, `to_dict()` | Abstraction (ABC), template method |
| `Person` → `Student` | Identity → learner with needs, preferences, history | **Inheritance**, **method overriding** (`validate`, `display_name`, `role`) |
| `Student` ◇ `Assessment` | Learner owns its history; `add_assessment` rejects duplicates | **Composition**, encapsulation (read-only `assessments`, `accessibility_needs` properties) |
| `Subject` ◇ `Topic` | Subject owns topics, prevents duplicate names | Composition |
| `Assessment` | Dated score; normalises to %; validates all fields | Encapsulation, derived properties |
| `Resource` (abstract) → `VideoResource`, `TextBasedResource` → `NotesResource`, `QuizResource`, `PracticeResource` | `requirement_for(need)` differs per category | **Polymorphism**, multi-level inheritance, self-registering **factory** (`__init_subclass__`, `Resource.create`) |
| `PerformanceAnalyzer` | Indicators, trend, status, priority | Single responsibility |
| `RecommendationRule` (abstract) → R1–R6 | Each rule evaluates a resource and returns an outcome with reason | **Strategy pattern / polymorphism**: the engine iterates over rule objects |
| `RecommendationEngine` | Runs the rules, selects and orders the plan | Composition of rules |
| `ReportBuilder` (abstract) → `LearnerReportBuilder`, `ClassSummaryBuilder` | Build JSON reports | Inheritance, overriding `build()` |
| `Repository` → `StudentRepository`, … | Row ↔ object mapping | Inheritance, separation of concerns |
| `Learn4AllService` | Application use-cases | Facade |
| `DomainError` → `ValidationError`, `NotFoundError`, `ConflictError` | Typed errors mapped to HTTP status codes | Exception hierarchy |

## 6. Algorithms and logic

**Normalisation:** `percentage = score / max_score × 100`.

**Weighted average** (configurable):
`w_i = type_weight(type_i) × (1 + recency_weight × i)` with `i` = 0 for the oldest attempt;
`weighted_avg = Σ w_i·p_i / Σ w_i`. Default weights: quiz 1, assignment 1.5, test 2, exam 3; recency 0.2.

**Trend:** least-squares slope of percentage vs attempt index. `≥ +3` improving, `≤ −3` declining,
otherwise stable (sensitivity configurable). **Improvement rate** = `(latest − first) / first × 100`.

**Topic status** (uses evidence, not a single test):

| Condition | Status |
|---|---|
| no valid assessments | `no_data` |
| weighted avg < weak threshold and count ≥ min_evidence | `weak` |
| weighted avg < weak threshold and count < min_evidence | `at_risk` (needs confirmation) |
| declining trend and latest < weak threshold | `at_risk` |
| weighted avg ≥ mastery, enough evidence, not declining | `mastered` |
| between thresholds, below midpoint | `developing` |
| otherwise | `proficient` |

**Gap priority:** `(mastery − weighted_avg) × severity + 10 if declining`, with severity weak 1.0,
at_risk 0.8, developing 0.5. Labels: ≥35 high, ≥20 medium, otherwise low.

**Recommendation rules:**

| Rule | Type | Logic |
|---|---|---|
| R1 Topic relevance | filter | Only gap topics. Mastered/proficient topics are excluded with a reason. Adds priority ÷ 10 |
| R2 Accessibility | filter | Each declared need that applies to the resource type must be supported (polymorphic `requirement_for`) |
| R3 Difficulty fit | filter + score | Target is beginner for below-threshold gaps, otherwise intermediate. Exact match +3, one level easier +1, one harder 0, two harder excluded |
| R4 Learning strategy | score | Rebuild (weak/at-risk): notes/video +2. Consolidate (developing): practice/quiz +2 |
| R5 Preference | score | +1.5 if the category is in the learner's preferences |
| R6 Time efficiency | score | ≤15 min +1, ≤30 min +0.5, >60 min −0.5 |

**Selection:** each gap (highest priority first) gets its best resource. Remaining slots are then
filled by score, with at most `max_per_topic` per topic and `max_recommendations` in total. Items are flagged
when they go beyond the learner's weekly study-time budget. Gaps with no eligible resource are reported to
the teacher as "uncovered".

## 7. Input → output flow

1. Teacher adds learners, subjects/topics, resources (UI forms or API).
2. Assessments are entered one by one or bulk-imported (CSV/JSON).
3. Validation: field checks (`Assessment.validate`), cross-entity checks (learner/topic exist and are
   consistent), and a duplicate check. Accepted rows are stored; rejected rows go to `validation_log`.
4. On request, `PerformanceAnalyzer` computes indicators from valid records only.
5. `RecommendationEngine` evaluates every resource with R1–R6 and builds the plan.
6. `LearnerReportBuilder` / `ClassSummaryBuilder` assemble JSON reports: summary, topic table,
   strengths, weak topics, trends, plan, exclusions, next actions, data issues and rules.
7. The frontend renders them (charts, tables, cards) or exports JSON. Print is also supported.

## 8. Testing

`backend/tests/test_learn4all.py`: **27 automated tests** (`python3 -m unittest discover -s tests -v`).

| Area | Examples |
|---|---|
| Validation | score > max, missing date, future/invalid date, non-numeric/negative score, bad type, duplicates, invalid e-mail/needs |
| OOP | inheritance/overriding, composition (duplicate topic), factory & polymorphic accessibility rules |
| Analytics | slope, weak vs at-risk (evidence), mastered, declining, type weights, configurable threshold |
| Recommendations | Reproduces the sample case (Mira, Loops 45/52 → 48.5%, captions): captioned video ranked first; uncaptioned, mastered and too-advanced resources excluded; every item explained |
| API (end-to-end) | Real HTTP server + temp DB: CRUD, 404/405/409/422/400 handling, bulk CSV, reports, settings validation |

Manual demo checklist: open Mira's report (captions), Arjun (screen reader: audio-described video and accessible notes only),
Priya (8 rejected records shown), Zoya (declining), the dashboard, a bulk import with mixed valid/invalid rows,
and changing the weak threshold in Settings to see statuses update.

## 9. Limitations

* Rule-based, not statistical: thresholds and points are reasonable defaults, not validated pedagogy.
* Simple linear trend; no seasonality, no anomaly detection, no confidence intervals.
* Accessibility metadata is a fixed vocabulary; real accessibility is richer (e.g. WCAG level, reading age).
* No authentication or roles. Intended for a trusted local network or demo use.
* Single-file SQLite with short-lived connections is fine for a class or a school, not for large scale.
* Sample data is fictional.

## 10. Future scope

* Authentication with teacher/learner/parent roles, and per-class data separation.
* Learner feedback loop: mark resources as completed or helpful, and down-rank what didn't help.
* Smarter analytics: exponential smoothing, anomaly alerts, predicted scores, spaced-repetition scheduling.
* Richer accessibility profiles (language, reading level, assistive tech), plus multilingual resources.
* CSV/PDF exports, LMS integration (LTI / xAPI), and offline mobile client using the same API.
* Optional ML ranking trained on outcomes, keeping rule explanations as guard-rails.
