from flask import current_app

from app.services.chat_prompts import build_chat_prompt, suggest_actions
from app.services.providers import gemini_provider
from app.services.prompt_versions import prompt_version
from app.services.conversation_context import build_conversation_context
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
    reply_request = build_chat_reply_request(
        user,
        conversation,
        user_message,
        include_latest_cv=include_latest_cv,
        cv_id=cv_id,
        history=history,
        job_description=job_description,
    )
    provider = reply_request["provider"]

    if provider != "gemini":
        reply = f"The configured AI provider '{provider}' is not available yet."
    else:
        reply = gemini_provider.generate_text(reply_request["prompt"])

    return finalize_chat_reply(reply_request, user_message, reply)


def stream_chat_reply(
    user,
    conversation,
    user_message,
    include_latest_cv=True,
    cv_id=None,
    history=None,
    job_description=None,
):
    reply_request = build_chat_reply_request(
        user,
        conversation,
        user_message,
        include_latest_cv=include_latest_cv,
        cv_id=cv_id,
        history=history,
        job_description=job_description,
    )
    provider = reply_request["provider"]

    if provider != "gemini":
        response_stream = iter(
            [f"The configured AI provider '{provider}' is not available yet."]
        )
    else:
        response_stream = gemini_provider.generate_text_stream(reply_request["prompt"])

    return response_stream, reply_request


def build_chat_reply_request(
    user,
    conversation,
    user_message,
    include_latest_cv=True,
    cv_id=None,
    history=None,
    job_description=None,
):
    conversation_context = build_conversation_context(
        user,
        conversation,
        user_message,
        include_latest_cv=include_latest_cv,
        cv_id=cv_id,
        job_description=job_description,
        history=history,
    )
    student_context = build_student_context(
        user,
        include_latest_cv=include_latest_cv,
        cv_id=cv_id,
    )
    history_messages = conversation_context.conversation_history
    active_job_description = conversation_context.active_job_description
    prompt = build_chat_prompt(
        user_message,
        student_context,
        history_messages,
        job_description=active_job_description,
        conversation_context=conversation_context,
    )
    provider = current_app.config.get("AI_PROVIDER", "gemini")

    return {
        "prompt": prompt,
        "used_latest_cv": conversation_context.has_cv,
        "latest_cv_filename": (
            conversation_context.active_cv["filename"]
            if conversation_context.active_cv
            else ""
        ),
        "detected_skills": (
            conversation_context.active_cv.get("detected_skills", [])
            if conversation_context.active_cv
            else []
        ),
        "used_job_description": bool(active_job_description),
        "active_job_description": active_job_description,
        "job_description_excerpt": _text_excerpt(active_job_description, limit=180),
        "prompt_version": prompt_version("chat_reply"),
        "provider": provider,
    }


def finalize_chat_reply(reply_request, user_message, reply):
    return {
        "reply": reply,
        "suggested_actions": suggest_actions(
            user_message,
            reply,
            job_description=reply_request.get("active_job_description"),
        ),
        "used_latest_cv": reply_request["used_latest_cv"],
        "latest_cv_filename": reply_request["latest_cv_filename"],
        "detected_skills": reply_request["detected_skills"],
        "used_job_description": reply_request["used_job_description"],
        "job_description_excerpt": reply_request["job_description_excerpt"],
        "prompt_version": reply_request["prompt_version"],
        "provider": reply_request["provider"],
    }


def _text_excerpt(text, limit=180):
    excerpt = " ".join((text or "").split())
    if len(excerpt) <= limit:
        return excerpt
    return f"{excerpt[: limit - 3].rstrip()}..."
