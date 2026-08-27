ACTIVE_PROMPT_VERSIONS = {
    "chat_reply": "chat-reply-v3.0",
    "cover_letter": "cover-letter-v3.0",
    "cv_tailoring_plan": "cv-tailoring-plan-v3.0",
    "interview_prep": "interview-prep-v3.0",
    "skill_gap_plan": "skill-gap-plan-v3.0",
    "career_roadmap": "career-roadmap-v3.0",
}


def prompt_version(key):
    return ACTIVE_PROMPT_VERSIONS.get(key, "unknown")
