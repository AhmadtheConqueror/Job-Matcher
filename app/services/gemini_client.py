import errno

import httpx
import requests
from flask import current_app, has_app_context
from google import genai
from google.genai import errors as genai_errors

AI_REQUEST_FAILED_PREFIX = "Gemini request failed."
AI_REQUEST_FAILED_MESSAGE = (
    f"{AI_REQUEST_FAILED_PREFIX} The app could not reach the AI service. "
    "Check network/firewall permissions and try again."
)
PLACEHOLDER_API_KEY = "paste-your-google-ai-studio-api-key-here"


def get_gemini_client():
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key or api_key == PLACEHOLDER_API_KEY:
        return None

    http_options = _gemini_http_options()
    if http_options:
        return genai.Client(api_key=api_key, http_options=http_options)
    return genai.Client(api_key=api_key)


def generate_gemini_text(prompt, system_instruction=""):
    client = get_gemini_client()
    if client is None:
        return None

    api_mode = current_app.config.get("GEMINI_API_MODE", "interactions")
    if api_mode == "generate_content":
        contents = prompt
        if system_instruction:
            contents = f"{system_instruction}\n\n{prompt}"
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=contents,
        )
        return (response.text or "").strip()

    request_kwargs = {
        "model": current_app.config["GEMINI_MODEL"],
        "input": prompt,
    }
    if system_instruction:
        request_kwargs["system_instruction"] = system_instruction

    interaction = client.interactions.create(**request_kwargs)
    return (getattr(interaction, "output_text", "") or "").strip()


def generate_gemini_text_stream(prompt, system_instruction=""):
    client = get_gemini_client()
    if client is None:
        return None

    api_mode = current_app.config.get("GEMINI_API_MODE", "interactions")
    if api_mode == "generate_content":
        contents = prompt
        if system_instruction:
            contents = f"{system_instruction}\n\n{prompt}"
        return _stream_generate_content(client, contents)

    request_kwargs = {
        "model": current_app.config["GEMINI_MODEL"],
        "input": prompt,
        "stream": True,
    }
    if system_instruction:
        request_kwargs["system_instruction"] = system_instruction

    return _stream_interaction_text(client, request_kwargs)


def _stream_generate_content(client, contents):
    for chunk in client.models.generate_content_stream(
        model=current_app.config["GEMINI_MODEL"],
        contents=contents,
    ):
        text = getattr(chunk, "text", "") or ""
        if text:
            yield text


def _stream_interaction_text(client, request_kwargs):
    stream = client.interactions.create(**request_kwargs)
    for event in stream:
        text = _interaction_event_text(event)
        if text:
            yield text


def _interaction_event_text(event):
    """Extract text from current 2.x step events and older event doubles."""
    event_type = getattr(event, "event_type", "")
    if event_type == "step.delta":
        delta = getattr(event, "delta", None)
    elif event_type == "content.delta":
        delta = getattr(event, "delta", None)
    else:
        return ""

    if getattr(delta, "type", "") != "text":
        return ""
    return getattr(delta, "text", "") or ""


def describe_gemini_error(error):
    if isinstance(error, genai_errors.APIError):
        return _describe_api_error(error)

    if _is_socket_permission_error(error):
        return (
            f"{AI_REQUEST_FAILED_PREFIX} Outbound socket access was blocked "
            "([WinError 10013]). Allow Python/Flask through your firewall or "
            "run the server outside a restricted sandbox, then try again."
        )

    if _is_timeout_error(error):
        return (
            f"{AI_REQUEST_FAILED_PREFIX} The request to Google AI timed out. "
            "Check your connection or increase GEMINI_TIMEOUT_MS in .env."
        )

    if _is_connectivity_error(error):
        return (
            f"{AI_REQUEST_FAILED_PREFIX} The app could not connect to Google AI. "
            "Check internet, VPN/proxy, DNS, and firewall settings."
        )

    return AI_REQUEST_FAILED_MESSAGE


def is_ai_error_response(text):
    if not isinstance(text, str):
        return False
    return (text or "").startswith((AI_REQUEST_FAILED_PREFIX, "AI request failed:"))


def _gemini_http_options():
    timeout_ms = current_app.config.get("GEMINI_TIMEOUT_MS")
    try:
        timeout_ms = int(timeout_ms)
    except (TypeError, ValueError):
        return None

    if timeout_ms <= 0:
        return None
    return {"timeout": timeout_ms}


def _describe_api_error(error):
    code = getattr(error, "code", None)
    status = getattr(error, "status", None)
    label = _api_error_label(code, status)
    suffix = f" ({label})." if label else "."

    if code in {401, 403}:
        return (
            f"{AI_REQUEST_FAILED_PREFIX} Google rejected GEMINI_API_KEY or the "
            f"linked project permissions{suffix} Create or migrate to a current "
            "Google AI Studio Gemini API key, then check key restrictions, "
            "billing/access, and restart Flask."
        )

    if code == 404:
        model = (
            current_app.config.get("GEMINI_MODEL", "the configured model")
            if has_app_context()
            else "the configured model"
        )
        return (
            f"{AI_REQUEST_FAILED_PREFIX} Google could not find the configured "
            f"model '{model}'{suffix} Check GEMINI_MODEL in .env."
        )

    if code == 429:
        return (
            f"{AI_REQUEST_FAILED_PREFIX} Gemini quota or rate limits were hit"
            f"{suffix} Wait a moment, check quota, or switch to a model/project "
            "with available capacity."
        )

    if code and 400 <= code < 500:
        return (
            f"{AI_REQUEST_FAILED_PREFIX} Google rejected the request{suffix} "
            "Check the model name, prompt size, and attached CV/job text."
        )

    if code and code >= 500:
        return (
            f"{AI_REQUEST_FAILED_PREFIX} Google AI returned a temporary server "
            f"error{suffix} Try again shortly."
        )

    return AI_REQUEST_FAILED_MESSAGE


def _api_error_label(code, status):
    parts = []
    if code:
        parts.append(f"HTTP {code}")
    if status:
        parts.append(str(status))
    return " ".join(parts)


def _is_timeout_error(error):
    timeout_types = (
        httpx.TimeoutException,
        requests.exceptions.Timeout,
        TimeoutError,
    )
    return any(isinstance(item, timeout_types) for item in _exception_chain(error))


def _is_connectivity_error(error):
    connectivity_types = (
        httpx.NetworkError,
        requests.exceptions.ConnectionError,
        OSError,
    )
    return any(isinstance(item, connectivity_types) for item in _exception_chain(error))


def _is_socket_permission_error(error):
    for item in _exception_chain(error):
        if getattr(item, "winerror", None) == 10013:
            return True
        if getattr(item, "errno", None) in {errno.EACCES, 10013}:
            return True
        text = str(item).lower()
        if "winerror 10013" in text:
            return True
        if "forbidden by its access permissions" in text:
            return True
    return False


def _exception_chain(error):
    seen = set()
    current = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__
