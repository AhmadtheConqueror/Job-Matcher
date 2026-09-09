import json
import re


COVER_LETTER_FIELDS = (
    "candidate_name",
    "contact_line",
    "date",
    "recipient_name",
    "company",
    "company_location",
    "subject",
    "salutation",
    "opening_paragraph",
    "experience_paragraph",
    "skills_paragraph",
    "closing_paragraph",
    "sign_off",
    "candidate_name_signature",
    "portfolio_url",
)

PARAGRAPH_FIELDS = (
    "opening_paragraph",
    "experience_paragraph",
    "skills_paragraph",
    "closing_paragraph",
)

SIGN_OFFS = {
    "sincerely,",
    "kind regards,",
    "best regards,",
    "regards,",
}

STYLE_OPTIONS = {
    "professional": "Professional",
    "concise": "Concise",
    "warm": "Warm & Personal",
}

LENGTH_OPTIONS = {
    "standard": "Standard",
    "short": "Short",
}


def parse_cover_letter_response(response_text, role_title="", company=""):
    parsed = _load_json_object(response_text)
    if isinstance(parsed, dict):
        return normalize_cover_letter(parsed, role_title=role_title, company=company)
    return _fallback_from_plain_text(response_text, role_title=role_title, company=company)


def normalize_cover_letter(data=None, role_title="", company=""):
    data = data or {}
    letter = {field: _clean_value(data.get(field, "")) for field in COVER_LETTER_FIELDS}

    if company and not letter["company"]:
        letter["company"] = _clean_value(company)
    if role_title and not letter["subject"]:
        letter["subject"] = f"Application for {role_title}"
    if not letter["salutation"]:
        letter["salutation"] = "Dear Hiring Manager,"
    if not letter["sign_off"]:
        letter["sign_off"] = "Sincerely,"
    if not letter["candidate_name_signature"] and letter["candidate_name"]:
        letter["candidate_name_signature"] = letter["candidate_name"]

    return letter


def serialize_cover_letter(letter):
    return json.dumps(normalize_cover_letter(letter), separators=(",", ":"))


def deserialize_cover_letter(payload):
    try:
        data = json.loads(payload or "{}")
    except json.JSONDecodeError:
        data = {}
    return normalize_cover_letter(data)


def cover_letter_paragraphs(letter):
    normalized = normalize_cover_letter(letter)
    return [normalized[field] for field in PARAGRAPH_FIELDS if normalized[field]]


def cover_letter_to_text(letter):
    normalized = normalize_cover_letter(letter)
    lines = []

    if normalized["candidate_name"]:
        lines.append(normalized["candidate_name"])

    contact_parts = []
    if normalized["contact_line"]:
        contact_parts.append(normalized["contact_line"])
    if normalized["portfolio_url"]:
        contact_parts.append(normalized["portfolio_url"])
    if contact_parts:
        lines.append(" | ".join(contact_parts))

    if normalized["date"]:
        lines.extend(["", normalized["date"]])

    recipient_lines = [
        normalized["recipient_name"],
        normalized["company"],
        normalized["company_location"],
    ]
    recipient_lines = [line for line in recipient_lines if line]
    if recipient_lines:
        lines.extend(["", *recipient_lines])

    if normalized["subject"]:
        lines.extend(["", normalized["subject"]])

    lines.extend(["", normalized["salutation"]])
    for paragraph in cover_letter_paragraphs(normalized):
        lines.extend(["", paragraph])

    sign_off = normalized["sign_off"]
    signature = normalized["candidate_name_signature"]
    if sign_off or signature:
        lines.append("")
    if sign_off:
        lines.append(sign_off)
    if signature:
        lines.append(signature)

    return "\n".join(lines).strip()


def _load_json_object(response_text):
    text = (response_text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _fallback_from_plain_text(response_text, role_title="", company=""):
    raw_paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", response_text or "")
        if _clean_value(paragraph)
    ]
    raw_paragraphs = [
        paragraph
        for paragraph in raw_paragraphs
        if _clean_value(paragraph).lower().strip(":") not in {"cover letter", "draft", "letter"}
    ]

    letter = normalize_cover_letter({}, role_title=role_title, company=company)
    if raw_paragraphs and _clean_value(raw_paragraphs[0]).lower().startswith("dear "):
        letter["salutation"] = _clean_value(raw_paragraphs.pop(0))

    if raw_paragraphs:
        sign_off = _extract_sign_off(raw_paragraphs[-1])
        if sign_off:
            letter["sign_off"] = sign_off["sign_off"]
            letter["candidate_name_signature"] = sign_off["signature"]
            raw_paragraphs.pop()

    paragraphs = [_clean_value(paragraph) for paragraph in raw_paragraphs]
    for field, paragraph in zip(PARAGRAPH_FIELDS, paragraphs[:4]):
        letter[field] = paragraph

    return letter


def _extract_sign_off(paragraph):
    lines = [
        _clean_value(line)
        for line in str(paragraph or "").splitlines()
        if _clean_value(line)
    ]
    if not lines:
        return None

    first_line = lines[0].lower()
    if first_line in SIGN_OFFS:
        return {
            "sign_off": lines[0],
            "signature": " ".join(lines[1:]),
        }

    text = _clean_value(paragraph)
    lower_text = text.lower()
    for sign_off in SIGN_OFFS:
        if lower_text.startswith(sign_off):
            signature = text[len(sign_off):].strip(" ,")
            return {
                "sign_off": text[: len(sign_off)],
                "signature": signature,
            }

    return None


def _clean_value(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item).strip() for item in value if str(item).strip())

    text = str(value).strip()
    if _is_placeholder(text):
        return ""

    text = re.sub(r"^#+\s*", "", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\[(date|insert[^\]]*|link to[^\]]*|portfolio[^\]]*)\]", "", text, flags=re.IGNORECASE)
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_placeholder(text):
    return bool(re.fullmatch(r"\[[^\]]+\]", text.strip()))
