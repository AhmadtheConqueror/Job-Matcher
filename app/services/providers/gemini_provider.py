from flask import current_app
from google import genai

from app.services.ai import AI_REQUEST_FAILED_MESSAGE


def generate_text(prompt):
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key or api_key == "paste-your-google-ai-studio-api-key-here":
        return (
            "Chat is wired up, but GEMINI_API_KEY is not configured yet. "
            "Add your Google AI Studio key to .env, restart Flask, and try again."
        )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=prompt,
        )
        return (response.text or "").strip()
    except Exception:
        current_app.logger.exception("Gemini chatbot request failed")
        return AI_REQUEST_FAILED_MESSAGE
