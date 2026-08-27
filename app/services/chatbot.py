from flask import current_app

from app.models import ChatMessage
from app.services.chat_prompts import build_chat_prompt, suggest_actions
from app.services.providers import gemini_provider
from app.services.prompt_versions import prompt_version
from app.services.student_context import build_student_context


def generate_chat_reply(
    user,
    conversation,
    user_message,
    include_latest_cv=True,
    cv_id=None,
    history=None,
    job_description=None,
):
    student_context = build_student_context(
        user,
        include_latest_cv=include_latest_cv,
        cv_id=cv_id,
    )
    history_messages = history if history is not None else _recent_messages(conversation)
    active_job_description = (job_description or "").strip()
    prompt = build_chat_prompt(
        user_message,
        student_context,
        history_messages,
        job_description=active_job_description,
    )
    provider = current_app.config.get("AI_PROVIDER", "gemini")

    if provider != "gemini":
        reply = f"The configured AI provider '{provider}' is not available yet."
    else:
        reply = gemini_provider.generate_text(prompt)

    return {
        "reply": reply,
        "suggested_actions": suggest_actions(
            user_message,
            reply,
            job_description=active_job_description,
        ),
        "used_latest_cv": student_context["used_latest_cv"],
        "latest_cv_filename": student_context["latest_cv_filename"],
        "detected_skills": student_context["detected_skills"],
        "used_job_description": bool(active_job_description),
        "job_description_excerpt": _text_excerpt(active_job_description, limit=180),
        "prompt_version": prompt_version("chat_reply"),
        "provider": provider,
    }


def _recent_messages(conversation, limit=8):
    if not conversation or not conversation.id:
        return []

    messages = (
        ChatMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


def _text_excerpt(text, limit=180):
    excerpt = " ".join((text or "").split())
    if len(excerpt) <= limit:
        return excerpt
    return f"{excerpt[: limit - 3].rstrip()}..."
