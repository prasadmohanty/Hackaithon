"""Automated tests (standard library unittest).

Run from the backend folder:   python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learn4all.analytics import PerformanceAnalyzer, slope  # noqa: E402
from learn4all.api import create_server  # noqa: E402
from learn4all.config import default_settings  # noqa: E402
from learn4all.database import Database  # noqa: E402
from learn4all.models import (Assessment, ConflictError, NotesResource, PracticeResource, Resource,  # noqa: E402
                              Student, Subject, Topic, ValidationError, VideoResource)
from learn4all.recommender import RecommendationEngine  # noqa: E402
from learn4all.seed import seed_demo_data  # noqa: E402
from learn4all.services import Learn4AllService  # noqa: E402

TODAY = date.today()


def days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


class ModelValidationTests(unittest.TestCase):
    def test_valid_assessment(self):
        a = Assessment(1, 1, days_ago(3), 45, 50, "quiz")
        self.assertEqual(a.validate(), [])
        self.assertEqual(a.percentage, 90.0)

    def test_invalid_assessments_report_each_field(self):
        cases = {
            "score": Assessment(1, 1, days_ago(1), 120, 100),          # above max (inconsistent)
            "date": Assessment(1, 1, "", 50),                          # missing
            "assessment_type": Assessment(1, 1, days_ago(1), 50, assessment_type="homework"),
            "max_score": Assessment(1, 1, days_ago(1), 5, 0),
        }
        for field, a in cases.items():
            with self.subTest(field=field):
                self.assertIn(field, [e["field"] for e in a.validate()])

    def test_future_and_malformed_dates(self):
        self.assertTrue(Assessment(1, 1, (TODAY + timedelta(days=2)).isoformat(), 50).validate())
        self.assertTrue(Assessment(1, 1, "2026-13-45", 50).validate())

    def test_non_numeric_and_negative_scores(self):
        self.assertIn("score", [e["field"] for e in Assessment(1, 1, days_ago(1), "eighty").validate()])
        self.assertIn("score", [e["field"] for e in Assessment(1, 1, days_ago(1), -1).validate()])

    def test_student_rejects_duplicate_assessment(self):
        s = Student("Mira", id=1)
        s.add_assessment(Assessment(1, 2, days_ago(5), 50, assessment_type="quiz"))
        with self.assertRaises(ConflictError):
            s.add_assessment(Assessment(1, 2, days_ago(5), 70, assessment_type="quiz"))

    def test_student_validation(self):
        self.assertTrue(Student("").validate())
        self.assertTrue(Student("A", email="not-an-email").validate())
        self.assertTrue(Student("A", accessibility_needs=["telepathy"]).validate())
        self.assertEqual(Student("A", accessibility_needs="captions, screen-reader").accessibility_needs,
                         frozenset({"captions", "screen-reader"}))

    def test_inheritance_and_overriding(self):
        s = Student("Mira", grade_level="Grade 8")
        self.assertEqual(s.role, "student")
        self.assertEqual(s.display_name(), "Mira (Grade 8)")

    def test_subject_composition(self):
        subj = Subject("PY101", "Python", id=1)
        subj.add_topic(Topic(None, "Loops"))
        with self.assertRaises(ValidationError):
            subj.add_topic(Topic(None, "loops"))
        self.assertEqual(subj.topics[0].subject_id, 1)


class PolymorphismTests(unittest.TestCase):
    def test_factory_returns_subclass(self):
        r = Resource.create("video", title="T", topic_id=1, difficulty="beginner", estimated_minutes=5)
        self.assertIsInstance(r, VideoResource)
        with self.assertRaises(ValidationError):
            Resource.create("podcast", title="T", topic_id=1, difficulty="beginner", estimated_minutes=5)

    def test_accessibility_rules_differ_by_category(self):
        video = VideoResource("V", 1, "beginner", 10, formats=[])
        notes = NotesResource("N", 1, "beginner", 10, formats=[])
        self.assertFalse(video.accessibility_check({"captions"})[0])   # video needs captions
        self.assertTrue(notes.accessibility_check({"captions"})[0])    # captions N/A for text
        self.assertFalse(notes.accessibility_check({"screen-reader"})[0])
        described = VideoResource("V2", 1, "beginner", 10, formats=["audio-description"])
        self.assertTrue(described.accessibility_check({"screen-reader"})[0])
        practice = PracticeResource("P", 1, "beginner", 10, formats=["transcript"])
        self.assertTrue(practice.accessibility_check({"screen-reader"})[0])


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.settings = default_settings()
        self.analyzer = PerformanceAnalyzer(self.settings)
        self.subject = Subject("PY101", "Python", id=1)
        self.topic = Topic(1, "Loops", id=1)

    def topic_perf(self, scores, types=None):
        items = [Assessment(1, 1, days_ago(50 - i * 7), s, 100, (types or ["test"] * len(scores))[i], id=i + 1)
                 for i, s in enumerate(scores)]
        return self.analyzer.analyse_topic(self.topic, self.subject, items)

    def test_slope(self):
        self.assertEqual(slope([10, 20, 30]), 10.0)
        self.assertIsNone(slope([50]))

    def test_weak_needs_historical_evidence(self):
        self.assertEqual(self.topic_perf([45]).status, "at_risk")          # single score: not confirmed
        self.assertEqual(self.topic_perf([45, 52]).status, "weak")         # two scores: confirmed

    def test_mastered_and_declining(self):
        self.assertEqual(self.topic_perf([88, 90, 92]).status, "mastered")
        tp = self.topic_perf([84, 76, 65, 54])
        self.assertEqual(tp.trend, "declining")
        self.assertIn(tp.status, ("at_risk", "weak", "developing"))
        self.assertEqual(tp.change, -30)

    def test_weighted_average_respects_type_weights(self):
        tp = self.topic_perf([40, 80], types=["quiz", "exam"])
        self.assertGreater(tp.weighted_average, tp.average)   # exam (weight 3) pulls up

    def test_threshold_is_configurable(self):
        self.settings["weak_threshold"] = 40
        self.assertNotEqual(self.topic_perf([45, 52]).status, "weak")


class RecommendationTests(unittest.TestCase):
    """Reproduces the sample solution scenario: Mira, loops vs variables, captions."""

    def setUp(self):
        self.settings = default_settings()
        subject = Subject("PY101", "Python", id=1)
        self.topics = {1: Topic(1, "Loops", id=1), 2: Topic(1, "Variables", id=2)}
        self.mira = Student("Mira", accessibility_needs=["captions"], id=1)
        items = [Assessment(1, 1, days_ago(14), 45, id=1), Assessment(1, 1, days_ago(7), 52, id=2),
                 Assessment(1, 2, days_ago(7), 82, id=3), Assessment(1, 2, days_ago(3), 90, id=4)]
        self.perf = PerformanceAnalyzer(self.settings).analyse_student(items, self.topics, {1: subject})
        self.resources = [
            VideoResource("Captioned loops video", 1, "beginner", 12, ["captions"], id=1),
            VideoResource("Uncaptioned loops video", 1, "beginner", 10, [], id=2),
            VideoResource("Variables advanced video", 2, "advanced", 15, ["captions"], id=3),
            NotesResource("Loops notes", 1, "beginner", 10, ["screen-reader"], id=4),
            PracticeResource("Loops expert challenge", 1, "advanced", 45, [], id=5),
        ]
        self.result = RecommendationEngine(self.settings).recommend(self.mira, self.perf, self.resources)

    def titles(self, key):
        return [x["resource"]["title"] for x in self.result[key]]

    def test_weak_topic_identified(self):
        self.assertEqual([g.topic_name for g in self.perf.gaps], ["Loops"])
        self.assertEqual(self.perf.topics[0].average, 48.5)

    def test_accessible_resource_recommended(self):
        self.assertEqual(self.titles("recommendations")[0], "Captioned loops video")
        self.assertIn("Loops notes", self.titles("recommendations"))   # captions N/A to notes

    def test_inaccessible_mastered_and_too_hard_excluded(self):
        excluded = self.titles("excluded")
        for title in ("Uncaptioned loops video", "Variables advanced video", "Loops expert challenge"):
            self.assertIn(title, excluded)
            self.assertNotIn(title, self.titles("recommendations"))

    def test_every_recommendation_is_explained(self):
        for rec in self.result["recommendations"]:
            self.assertTrue(rec["reasons"])
            self.assertEqual(rec["rule_trace"][0]["rule"], "R1")


class ApiIntegrationTests(unittest.TestCase):
    """Starts the real http.server on a free port with a temporary SQLite DB."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Database(os.path.join(cls.tmp.name, "test.db"))
        db.initialize()
        cls.service = Learn4AllService(db)
        cls.seed = seed_demo_data(cls.service)
        cls.server = create_server(cls.service, "127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def test_seed_includes_invalid_rows(self):
        self.assertEqual(self.seed["assessments_rejected"], 8)
        status, log = self.call("GET", "/api/validation-log")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(log["count"], 8)

    def test_health_meta_docs_openapi(self):
        for path in ("/api/health", "/api/meta", "/api/docs", "/api/openapi.json", "/api/rules"):
            with self.subTest(path=path):
                self.assertEqual(self.call("GET", path)[0], 200)

    def test_student_crud(self):
        status, s = self.call("POST", "/api/students", {"name": "Test Learner", "email": "t@x.example",
                                                        "accessibility_needs": ["large-print"]})
        self.assertEqual(status, 201)
        self.assertEqual(self.call("POST", "/api/students", {"name": "Dup", "email": "t@x.example"})[0], 409)
        status, s2 = self.call("PUT", f"/api/students/{s['id']}", {"weekly_study_minutes": 45})
        self.assertEqual((status, s2["weekly_study_minutes"], s2["name"]), (200, 45, "Test Learner"))
        self.assertEqual(self.call("DELETE", f"/api/students/{s['id']}")[0], 200)
        self.assertEqual(self.call("GET", f"/api/students/{s['id']}")[0], 404)

    def test_assessment_validation_over_http(self):
        status, err = self.call("POST", "/api/assessments", {"student_id": 1, "topic_id": 1, "date": days_ago(1),
                                                             "score": 150})
        self.assertEqual(status, 422)
        self.assertEqual(err["error"]["details"][0]["field"], "score")
        status, err = self.call("POST", "/api/assessments", {"student_id": 999, "topic_id": 1,
                                                             "date": days_ago(1), "score": 50})
        self.assertEqual(status, 422)
        ok = {"student_id": 1, "topic_id": 1, "date": days_ago(2), "score": 66, "assessment_type": "assignment"}
        self.assertEqual(self.call("POST", "/api/assessments", ok)[0], 201)
        self.assertEqual(self.call("POST", "/api/assessments", ok)[0], 409)   # duplicate

    def test_bulk_csv(self):
        csv_text = ("student_email,subject_code,topic_name,date,score\n"
                    f"leo@learn4all.example,PY101,Conditionals,{days_ago(1)},91\n"
                    f"leo@learn4all.example,PY101,Nope,{days_ago(1)},91\n")
        status, res = self.call("POST", "/api/assessments/bulk", {"csv": csv_text})
        self.assertEqual((status, res["accepted"], res["rejected"]), (200, 1, 1))

    def test_reports(self):
        status, report = self.call("GET", "/api/students/1/report")
        self.assertEqual(status, 200)
        for key in ("summary", "performance", "study_plan", "next_actions", "rules_explained"):
            self.assertIn(key, report)
        status, summary = self.call("GET", "/api/reports/class")
        self.assertEqual(status, 200)
        self.assertEqual(summary["totals"]["students"], self.seed["students"])

    def test_settings_validation(self):
        self.assertEqual(self.call("PUT", "/api/settings", {"weak_threshold": 95})[0], 422)  # >= mastery
        self.assertEqual(self.call("PUT", "/api/settings", {"unknown": 1})[0], 422)
        status, s = self.call("PUT", "/api/settings", {"weak_threshold": 55})
        self.assertEqual((status, s["values"]["weak_threshold"]), (200, 55.0))
        self.call("POST", "/api/settings/reset")

    def test_errors(self):
        self.assertEqual(self.call("GET", "/api/nothing")[0], 404)
        self.assertEqual(self.call("DELETE", "/api/meta")[0], 405)
        req = urllib.request.Request(self.base + "/api/students", data=b"{bad json", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
