"""Domain vocabularies shared by every layer of the backend."""

RESOURCE_CATEGORIES = ("video", "notes", "quiz", "practice")

DIFFICULTY_LEVELS = ("beginner", "intermediate", "advanced")

ASSESSMENT_TYPES = ("quiz", "assignment", "test", "exam")

# Accessibility needs a learner can declare, and formats a resource can offer.
ACCESSIBILITY_FORMATS = {
    "captions": "Closed captions for spoken audio",
    "transcript": "Full text transcript of audio/video content",
    "audio-description": "Narrated description of on-screen visuals",
    "sign-language": "Sign language interpretation",
    "screen-reader": "Structured content that works with screen readers",
    "large-print": "Large print / high-contrast layout",
    "dyslexia-friendly": "Dyslexia-friendly font, spacing and plain language",
}

# Topic status vocabulary produced by the analyser (ordered worst -> best).
TOPIC_STATUSES = {
    "weak": "Below the weak threshold, confirmed by enough historical evidence",
    "at_risk": "Below threshold on limited evidence, or declining below threshold",
    "developing": "Above the weak threshold but still well below mastery",
    "proficient": "Solid performance, approaching mastery",
    "mastered": "At or above mastery threshold with enough evidence and no decline",
    "no_data": "No valid assessments recorded yet",
}

GAP_STATUSES = ("weak", "at_risk", "developing")
STRENGTH_STATUSES = ("mastered", "proficient")
