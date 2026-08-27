import re
from html import escape

from markupsafe import Markup


HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
BULLET_RE = re.compile(r"^(?:[-*+]|\u2022)\s+(.+)$")
NUMBERED_RE = re.compile(r"^(\d+)[.)]\s+(.+)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)")
CODE_RE = re.compile(r"`([^`]+)`")


def format_text_blocks(text):
    """Turn simple Markdown-ish AI text into safe display blocks."""
    blocks = []
    paragraph_lines = []
    list_items = []
    list_kind = None

    def flush_paragraph():
        if paragraph_lines:
            content = " ".join(line.strip() for line in paragraph_lines if line.strip())
            if content:
                blocks.append({"kind": "paragraph", "content": content})
            paragraph_lines.clear()

    def flush_list():
        nonlocal list_kind
        if list_items:
            blocks.append({"kind": list_kind or "list", "entries": list_items.copy()})
            list_items.clear()
            list_kind = None

    def add_list_item(kind, item):
        nonlocal list_kind
        if list_kind and list_kind != kind:
            flush_list()
        list_kind = kind
        list_items.append(item.strip())

    for raw_line in (text or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            flush_list()
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush_paragraph()
            flush_list()
            blocks.append({"kind": "heading", "content": _clean_heading(heading_match.group(1))})
            continue

        bullet_match = BULLET_RE.match(line)
        if bullet_match:
            flush_paragraph()
            add_list_item("list", bullet_match.group(1))
            continue

        numbered_match = NUMBERED_RE.match(line)
        if numbered_match and _looks_like_section_heading(numbered_match.group(2)):
            flush_paragraph()
            flush_list()
            blocks.append({"kind": "heading", "content": _clean_heading(line)})
            continue
        if numbered_match:
            flush_paragraph()
            add_list_item("ordered_list", numbered_match.group(2))
            continue

        flush_list()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()
    return blocks


def render_inline_markup(text):
    safe_text = escape(text or "")
    safe_text = CODE_RE.sub(r"<code>\1</code>", safe_text)
    safe_text = BOLD_RE.sub(r"<strong>\1</strong>", safe_text)
    safe_text = ITALIC_RE.sub(r"<em>\1</em>", safe_text)
    return Markup(safe_text)


def render_inline_pdf_markup(text):
    safe_text = escape(_normalize_pdf_text(text or ""))
    safe_text = CODE_RE.sub(r'<font name="Courier">\1</font>', safe_text)
    safe_text = BOLD_RE.sub(r"<b>\1</b>", safe_text)
    safe_text = ITALIC_RE.sub(r"<i>\1</i>", safe_text)
    return safe_text


def _clean_heading(text):
    heading = text.strip()
    heading = re.sub(r"^\*{1,2}(.+?)\*{1,2}$", r"\1", heading)
    return heading


def _looks_like_section_heading(text):
    normalized = re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()
    section_heads = {
        "match summary",
        "strongest relevant experience",
        "missing or weak skills",
        "suggested cv improvements",
        "interview preparation points",
    }
    return normalized in section_heads


def _normalize_pdf_text(text):
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\ufffd": "-",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    return text
