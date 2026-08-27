import re


KNOWN_SKILLS = (
    "Python",
    "Flask",
    "Django",
    "FastAPI",
    "JavaScript",
    "TypeScript",
    "React",
    "Node.js",
    "HTML",
    "CSS",
    "Bootstrap",
    "Tailwind",
    "SQL",
    "SQLite",
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Git",
    "GitHub",
    "REST API",
    "API",
    "Docker",
    "Linux",
    "Windows",
    "Excel",
    "Power BI",
    "Microsoft 365",
    "Active Directory",
    "Azure",
    "AWS",
    "Networking",
    "TCP/IP",
    "Cybersecurity",
    "Troubleshooting",
    "Technical Support",
    "Database Design",
    "Authentication",
    "CRUD",
)

SECTION_ALIASES = {
    "education": ("education", "academic background", "qualification"),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "internship",
        "siwes",
        "industrial training",
    ),
    "projects": ("projects", "selected projects", "academic projects"),
    "skills": ("skills", "technical skills", "core skills", "technologies"),
    "certifications": ("certifications", "certificates", "training"),
}


def summarize_cv_text(cv_text):
    text = _normalize_text(cv_text)
    sections = _extract_sections(text)

    return {
        "detected_skills": _detect_skills(text),
        "education": _section_excerpt(sections, "education"),
        "experience": _section_excerpt(sections, "experience"),
        "projects": _section_excerpt(sections, "projects"),
        "skills_section": _section_excerpt(sections, "skills"),
        "certifications": _section_excerpt(sections, "certifications"),
        "profile_excerpt": _profile_excerpt(text, sections),
    }


def summarize_analysis_text(result_text):
    text = _normalize_text(result_text)
    lines = [line.strip("#* -") for line in text.splitlines() if line.strip()]
    useful_lines = []

    for line in lines:
        if len(line) < 4:
            continue
        useful_lines.append(line)
        if len(useful_lines) == 4:
            break

    return _clip_text(" ".join(useful_lines), 700)


def detect_known_skills(text):
    return _detect_skills(_normalize_text(text))


def _detect_skills(text):
    detected = []
    lowered = text.lower()

    for skill in KNOWN_SKILLS:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, lowered):
            detected.append(skill)

    return detected


def _extract_sections(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections = {key: [] for key in SECTION_ALIASES}
    current_key = None

    for line in lines:
        section_key = _section_key(line)
        if section_key:
            current_key = section_key
            continue
        if _looks_like_heading(line):
            current_key = None
            continue

        if current_key:
            sections[current_key].append(line)

    return sections


def _section_key(line):
    clean = re.sub(r"[^a-z ]+", " ", line.lower())
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean.split()) > 5:
        return None

    for key, aliases in SECTION_ALIASES.items():
        if clean in aliases:
            return key

    return None


def _looks_like_heading(line):
    clean = re.sub(r"[^A-Za-z ]+", "", line).strip()
    if not clean:
        return False
    words = clean.split()
    if len(words) > 5:
        return False
    return line.isupper() or all(word[:1].isupper() for word in words)


def _section_excerpt(sections, key, limit=900):
    return _clip_text(" ".join(sections.get(key) or []), limit)


def _profile_excerpt(text, sections, limit=1000):
    section_text = " ".join(line for values in sections.values() for line in values)
    if section_text:
        return _clip_text(section_text, limit)
    return _clip_text(text, limit)


def _normalize_text(text):
    text = (text or "").replace("\r\n", "\n")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return text


def _clip_text(text, limit):
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."
