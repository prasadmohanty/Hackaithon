"""Representative, fictional multi-student sample data.

Covers every scenario the brief asks for:
* several learners across three subjects with history over ~10 weeks
* learners with accessibility needs (captions, screen-reader, large-print,
  dyslexia-friendly, sign-language, transcript)
* a learner (Priya) with incomplete / invalid / duplicate / inconsistent
  records - these go through normal validation and land in the data-quality log
* improving (Kabir, Sara) and declining (Zoya) trends, a high performer (Leo)

Dates are relative to "today" so the sample never contains future dates.
"""

from __future__ import annotations

from datetime import date, timedelta

from .models import ConflictError, ValidationError

SUBJECTS = [
    ("PY101", "Python Programming", "Introductory programming with Python",
     ["Variables", "Data Types", "Conditionals", "Loops", "Functions", "OOP Basics"]),
    ("MATH8", "Mathematics", "Grade 8 mathematics",
     ["Fractions", "Algebra", "Geometry", "Statistics"]),
    ("ENG8", "English", "Grade 8 English language",
     ["Reading Comprehension", "Grammar", "Vocabulary"]),
]

STUDENTS = [
    {"name": "Mira Sharma", "email": "mira@learn4all.example", "grade_level": "Grade 8",
     "accessibility_needs": ["captions"], "preferred_categories": ["video"], "weekly_study_minutes": 90,
     "notes": "Hard of hearing - needs captions on all video content."},
    {"name": "Arjun Mehta", "email": "arjun@learn4all.example", "grade_level": "Grade 8",
     "accessibility_needs": ["screen-reader", "large-print"], "preferred_categories": ["notes"],
     "weekly_study_minutes": 120, "notes": "Low vision; uses a screen reader."},
    {"name": "Sara Khan", "email": "sara@learn4all.example", "grade_level": "Grade 8",
     "accessibility_needs": ["dyslexia-friendly"], "preferred_categories": ["practice"],
     "weekly_study_minutes": 100, "notes": "Dyslexia - prefers dyslexia-friendly formatting."},
    {"name": "Leo Fernandes", "email": "leo@learn4all.example", "grade_level": "Grade 8",
     "weekly_study_minutes": 60, "notes": "Consistently high achiever."},
    {"name": "Priya Nair", "email": "priya@learn4all.example", "grade_level": "Grade 8",
     "weekly_study_minutes": 120, "notes": "Several records submitted with errors (demo of validation)."},
    {"name": "Kabir Singh", "email": "kabir@learn4all.example", "grade_level": "Grade 8",
     "accessibility_needs": ["sign-language", "captions"], "preferred_categories": ["video", "quiz"],
     "weekly_study_minutes": 150, "notes": "Deaf - uses Indian Sign Language."},
    {"name": "Zoya Ali", "email": "zoya@learn4all.example", "grade_level": "Grade 8",
     "weekly_study_minutes": 120, "notes": "Recent drop in Python scores."},
    {"name": "Dev Patel", "email": "dev@learn4all.example", "grade_level": "Grade 8",
     "accessibility_needs": ["transcript"], "preferred_categories": ["practice", "quiz"],
     "weekly_study_minutes": 80, "notes": "Auditory processing - prefers transcripts."},
]

# email -> {(subject_code, topic): [chronological percentage scores]}
SCORES = {
    "mira@learn4all.example": {
        ("PY101", "Variables"): [82, 86, 88], ("PY101", "Data Types"): [74, 79],
        ("PY101", "Conditionals"): [66, 70, 72], ("PY101", "Loops"): [45, 52],
        ("PY101", "Functions"): [58, 55, 61], ("MATH8", "Fractions"): [70, 75],
        ("MATH8", "Algebra"): [62, 68, 71]},
    "arjun@learn4all.example": {
        ("PY101", "Variables"): [90, 92, 95], ("PY101", "Conditionals"): [88, 91],
        ("PY101", "Loops"): [85, 89, 93], ("PY101", "Functions"): [80, 84],
        ("MATH8", "Geometry"): [42, 48, 50], ("MATH8", "Statistics"): [55, 58],
        ("MATH8", "Algebra"): [76, 79]},
    "sara@learn4all.example": {
        ("ENG8", "Reading Comprehension"): [50, 58, 66, 72], ("ENG8", "Grammar"): [40, 46, 52],
        ("ENG8", "Vocabulary"): [62, 65], ("MATH8", "Fractions"): [78, 81]},
    "leo@learn4all.example": {
        ("PY101", "Variables"): [95, 97], ("PY101", "Loops"): [90, 94, 96],
        ("PY101", "Functions"): [88, 91, 93], ("PY101", "OOP Basics"): [86, 90],
        ("MATH8", "Algebra"): [91, 94], ("MATH8", "Statistics"): [89, 92],
        ("ENG8", "Vocabulary"): [72, 70]},
    "priya@learn4all.example": {
        ("PY101", "Variables"): [70, 74], ("PY101", "Loops"): [55],
        ("MATH8", "Algebra"): [64]},
    "kabir@learn4all.example": {
        ("MATH8", "Algebra"): [38, 49, 58, 67], ("MATH8", "Fractions"): [52, 57, 64],
        ("MATH8", "Geometry"): [70, 72], ("ENG8", "Vocabulary"): [60, 63]},
    "zoya@learn4all.example": {
        ("PY101", "Functions"): [84, 76, 65, 54], ("PY101", "OOP Basics"): [72, 64, 58],
        ("PY101", "Loops"): [80, 82], ("ENG8", "Reading Comprehension"): [88, 90]},
    "dev@learn4all.example": {
        ("PY101", "Data Types"): [58, 63], ("PY101", "OOP Basics"): [50, 55, 52],
        ("MATH8", "Statistics"): [68, 70]},
}

TYPES = ["quiz", "test", "assignment", "test", "exam"]
def offset_days(index: int, count: int) -> int:
    """Space attempts two weeks apart so the most recent one was a week ago."""
    return 7 + (count - 1 - index) * 14

# (subject, topic, category, difficulty, minutes, formats, title, description)
RESOURCES = [
    ("PY101", "Variables", "video", "advanced", 15, ["captions"], "Variables: Advanced Patterns",
     "Scope, mutability and naming conventions for confident programmers."),
    ("PY101", "Variables", "notes", "beginner", 10, ["screen-reader", "large-print"], "Variables Starter Notes",
     "What a variable is, assignment and naming rules."),
    ("PY101", "Data Types", "notes", "beginner", 12, ["screen-reader", "dyslexia-friendly"], "Data Types Explained",
     "int, float, str, bool, list and dict with plain-language examples."),
    ("PY101", "Data Types", "quiz", "intermediate", 10, ["screen-reader"], "Data Types Check-up Quiz",
     "Ten questions on type conversion and common pitfalls."),
    ("PY101", "Data Types", "practice", "beginner", 20, ["transcript", "dyslexia-friendly"], "Type Conversion Workshop",
     "Guided exercises converting between types, with transcripted walkthrough."),
    ("PY101", "Conditionals", "video", "intermediate", 15, ["captions", "sign-language"], "If / Elif / Else in Practice",
     "Decision making with real-life examples."),
    ("PY101", "Conditionals", "practice", "intermediate", 20, [], "Conditionals Practice Pack",
     "Twelve short problems on branching logic."),
    ("PY101", "Loops", "video", "beginner", 12, ["captions", "transcript"], "Loops Explained (Captioned)",
     "for and while loops step by step, fully captioned."),
    ("PY101", "Loops", "video", "beginner", 10, [], "Loops in 10 Minutes",
     "Fast-paced intro to loops (no captions available)."),
    ("PY101", "Loops", "notes", "beginner", 15, ["screen-reader", "large-print", "dyslexia-friendly"],
     "Loops Study Notes", "Accessible notes covering range(), iteration and loop control."),
    ("PY101", "Loops", "quiz", "beginner", 10, ["screen-reader"], "Loops Quick Quiz",
     "Check your understanding of for/while loops."),
    ("PY101", "Loops", "practice", "intermediate", 30, ["screen-reader"], "For & While Loop Practice Set",
     "Hands-on tasks: counters, accumulators and sentinels."),
    ("PY101", "Loops", "practice", "advanced", 45, [], "Nested Loops Challenge",
     "Pattern printing and matrix traversal challenges."),
    ("PY101", "Functions", "video", "beginner", 18, ["captions"], "Functions from Scratch",
     "Defining and calling functions, captioned."),
    ("PY101", "Functions", "notes", "beginner", 10, ["screen-reader", "dyslexia-friendly", "large-print"],
     "Functions Cheat Sheet", "def, parameters, return values and docstrings on one page."),
    ("PY101", "Functions", "practice", "intermediate", 25, ["screen-reader", "transcript"],
     "Parameters & Return Values Practice", "Write and test small reusable functions."),
    ("PY101", "Functions", "video", "advanced", 40, ["captions", "transcript"], "Recursion Deep Dive",
     "Recursive thinking with visual call stacks."),
    ("PY101", "OOP Basics", "video", "beginner", 20, ["captions", "transcript"], "Classes & Objects Intro",
     "Constructors, attributes and methods explained visually."),
    ("PY101", "OOP Basics", "notes", "beginner", 15, ["dyslexia-friendly", "screen-reader"], "OOP Basics Notes",
     "Encapsulation, inheritance and polymorphism in plain language."),
    ("PY101", "OOP Basics", "practice", "intermediate", 35, ["transcript"], "Build a Library System",
     "Mini-project modelling books and members with classes."),
    ("PY101", "OOP Basics", "quiz", "intermediate", 10, [], "OOP Concepts Quiz",
     "Quick self-check on OOP vocabulary."),
    ("MATH8", "Fractions", "video", "beginner", 12, ["captions", "sign-language"], "Fractions with Sign Language",
     "Equivalent fractions and simplification, ISL interpreted."),
    ("MATH8", "Fractions", "practice", "intermediate", 20, ["large-print"], "Fraction Operations Worksheet",
     "Add, subtract, multiply and divide fractions."),
    ("MATH8", "Fractions", "quiz", "beginner", 8, ["screen-reader", "dyslexia-friendly"], "Fractions Warm-up Quiz",
     "Eight quick questions."),
    ("MATH8", "Algebra", "video", "beginner", 15, ["captions", "sign-language", "transcript"],
     "Algebra Basics with ISL", "Variables, expressions and simple equations."),
    ("MATH8", "Algebra", "notes", "beginner", 12, ["screen-reader", "large-print"], "Solving Linear Equations Notes",
     "Step-by-step method with worked examples."),
    ("MATH8", "Algebra", "practice", "intermediate", 25, ["screen-reader", "large-print"], "Equation Practice Set",
     "Twenty graded linear-equation problems."),
    ("MATH8", "Algebra", "quiz", "intermediate", 10, ["screen-reader"], "Algebra Checkpoint Quiz",
     "Self-check for linear equations."),
    ("MATH8", "Geometry", "video", "beginner", 14, ["captions"], "Angles & Shapes Video",
     "Visual introduction to angles (no audio description)."),
    ("MATH8", "Geometry", "video", "beginner", 16, ["audio-description", "captions"], "Shapes & Angles (Audio-described)",
     "Every diagram is narrated for blind and low-vision learners."),
    ("MATH8", "Geometry", "notes", "beginner", 20, ["screen-reader", "large-print"], "Geometry Tactile & Audio Guide",
     "Screen-reader friendly notes with tactile diagram instructions."),
    ("MATH8", "Geometry", "practice", "advanced", 40, [], "Geometry Proof Challenge",
     "Multi-step proofs for advanced learners."),
    ("MATH8", "Statistics", "notes", "beginner", 15, ["screen-reader", "large-print"], "Mean, Median & Mode Notes",
     "Accessible notes on averages and spread."),
    ("MATH8", "Statistics", "video", "intermediate", 18, ["captions", "transcript"], "Reading Charts & Data",
     "Interpreting bar charts, histograms and tables."),
    ("MATH8", "Statistics", "practice", "intermediate", 25, [], "Data Handling Practice",
     "Collect, organise and summarise a small data set."),
    ("ENG8", "Reading Comprehension", "notes", "beginner", 15, ["dyslexia-friendly", "screen-reader"],
     "Active Reading Strategies", "Skimming, scanning and summarising."),
    ("ENG8", "Reading Comprehension", "practice", "intermediate", 20, ["dyslexia-friendly"],
     "Short Passages Practice", "Five passages with inference questions."),
    ("ENG8", "Reading Comprehension", "video", "intermediate", 12, ["captions"], "Finding the Main Idea",
     "Identify main ideas and supporting details."),
    ("ENG8", "Grammar", "video", "beginner", 10, ["captions", "transcript"], "Grammar Basics Video",
     "Parts of speech and sentence structure."),
    ("ENG8", "Grammar", "notes", "beginner", 12, [], "Grammar Rules Handout",
     "Dense reference handout (standard formatting only)."),
    ("ENG8", "Grammar", "notes", "beginner", 15, ["dyslexia-friendly", "large-print"], "Grammar Made Simple",
     "Dyslexia-friendly grammar guide with colour-coded examples."),
    ("ENG8", "Grammar", "quiz", "intermediate", 10, ["dyslexia-friendly"], "Grammar Self-check",
     "Ten sentence-correction questions."),
    ("ENG8", "Vocabulary", "quiz", "beginner", 8, ["screen-reader", "dyslexia-friendly"], "Word Power Quiz",
     "Synonyms, antonyms and context clues."),
    ("ENG8", "Vocabulary", "practice", "intermediate", 15, ["dyslexia-friendly"], "Vocabulary in Context",
     "Use new words in your own sentences."),
    ("ENG8", "Vocabulary", "video", "beginner", 10, ["sign-language", "captions"], "Everyday Vocabulary (ISL)",
     "Common academic words with sign language."),
]


def _invalid_rows(today: date, email: str) -> list:
    """Deliberately bad records for Priya: each one demonstrates a validation rule."""
    def d(days: int) -> str:
        return (today - timedelta(days=days)).isoformat()

    return [
        {"student_email": email, "subject_code": "PY101", "topic_name": "Functions",
         "date": d(30), "score": 120, "max_score": 100, "assessment_type": "test",
         "notes": "Score above maximum (inconsistent)"},
        {"student_email": email, "subject_code": "PY101", "topic_name": "Functions",
         "date": "", "score": 58, "assessment_type": "quiz", "notes": "Missing date"},
        {"student_email": email, "subject_code": "MATH8", "topic_name": "Geometry",
         "date": d(20), "score": "eighty", "assessment_type": "test", "notes": "Non-numeric score"},
        {"student_email": email, "subject_code": "MATH8", "topic_name": "Algebra",
         "date": (today + timedelta(days=5)).isoformat(), "score": 60, "assessment_type": "test",
         "notes": "Date in the future"},
        {"student_email": email, "subject_code": "PY101", "topic_name": "Variables",
         "date": d(offset_days(0, 2)), "score": 70, "assessment_type": TYPES[0], "notes": "Duplicate entry"},
        {"student_email": email, "subject_code": "PY101", "topic_name": "Recursion",
         "date": d(14), "score": 65, "assessment_type": "quiz", "notes": "Unknown topic"},
        {"student_email": email, "subject_code": "ENG8", "topic_name": "Grammar",
         "date": d(10), "score": 61, "assessment_type": "homework", "notes": "Invalid assessment type"},
        {"student_email": email, "subject_code": "ENG8", "topic_name": "Grammar",
         "date": d(10), "score": -5, "assessment_type": "quiz", "notes": "Negative score"},
    ]


def seed_demo_data(service, today: date = None) -> dict:
    """Populate an empty database through the service (so all validation applies)."""
    today = today or date.today()
    subjects = {}
    for code, name, description, topics in SUBJECTS:
        subjects[code] = service.create_subject(
            {"code": code, "name": name, "description": description, "topics": topics})
    topic_ids = {(code, t["name"]): t["id"] for code, s in subjects.items() for t in s["topics"]}

    students = {s["email"]: service.create_student(s) for s in STUDENTS}

    created = rejected = 0
    for email, topics in SCORES.items():
        for (code, topic), scores in topics.items():
            for i, score in enumerate(scores):
                service.create_assessment({
                    "student_id": students[email]["id"], "topic_id": topic_ids[(code, topic)],
                    "date": (today - timedelta(days=offset_days(i, len(scores)))).isoformat(),
                    "score": score, "max_score": 100, "assessment_type": TYPES[i]}, source="seed")
                created += 1

    for row in _invalid_rows(today, "priya@learn4all.example"):
        try:
            service.create_assessment(row, source="seed")
            created += 1
        except (ValidationError, ConflictError):
            rejected += 1

    for code, topic, category, difficulty, minutes, formats, title, description in RESOURCES:
        slug = title.lower().replace(" ", "-").replace("&", "and").replace("/", "-").replace("(", "").replace(")", "")
        service.create_resource({
            "title": title, "topic_id": topic_ids[(code, topic)], "category": category,
            "difficulty": difficulty, "estimated_minutes": minutes, "formats": formats,
            "url": f"https://example.org/learn4all/{slug}", "description": description})

    return {"subjects": len(subjects), "topics": len(topic_ids), "students": len(students),
            "assessments_created": created, "assessments_rejected": rejected,
            "resources": len(RESOURCES)}
