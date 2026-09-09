from flask import current_app

from app.services.gemini_client import (
    describe_gemini_error,
    generate_gemini_text,
    generate_gemini_text_stream,
)


def generate_text(prompt):
    try:
        response_text = generate_gemini_text(prompt)
        if response_text is None:
            return (
                "Chat is wired up, but GEMINI_API_KEY is not configured yet. "
                "Add your Google AI Studio key to .env, restart Flask, and try again."
            )
        return response_text
    except Exception as exc:
        current_app.logger.exception("Gemini chatbot request failed")
        return describe_gemini_error(exc)


def generate_text_stream(prompt):
    response_stream = generate_gemini_text_stream(prompt)
    if response_stream is None:
        return iter(
            [
                (
                    "Chat is wired up, but GEMINI_API_KEY is not configured yet. "
                    "Add your Google AI Studio key to .env, restart Flask, and try again."
                )
            ]
        )
    return response_stream
