from app.services.cover_letter import parse_cover_letter_response

from flask import current_app
from google import genai

AI_REQUEST_FAILED_MESSAGE = (
    "Gemini request failed. The app could not reach the AI service. "
    "Check network/firewall permissions and try again."
)


def _get_client():
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key or api_key == "paste-your-google-ai-studio-api-key-here":
        return None
    return genai.Client(api_key=api_key)


def _placeholder_response(feature_name):
    return (
        f"{feature_name} is wired up, but GEMINI_API_KEY is not configured yet.\n\n"
        "Add your Google AI Studio key to .env, restart Flask, and this screen "
        "will return a real AI-generated response."
    )


def is_ai_error_response(text):
    if not isinstance(text, str):
        return False
    return (text or "").startswith((AI_REQUEST_FAILED_MESSAGE, "AI request failed:"))


def analyze_cv_against_job(cv_text, job_text):
    client = _get_client()
    if client is None:
        return _placeholder_response("CV analysis")

    prompt = f"""
Analyze this CV against the job description.

Return clean Markdown only, using these exact headings:
## 1. Match Summary
## 2. Strongest Relevant Experience
## 3. Missing or Weak Skills
## 4. Suggested CV Improvements
## 5. Interview Preparation Points

Under each heading, use either one short paragraph or 2-4 concise bullet
points. Avoid tables, code fences, long unbroken paragraphs, and decorative
symbols. Be practical, specific, and easy to scan.

CV:
{cv_text}

Job description:
{job_text}
"""

    try:
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=(
                "You are a practical, concise career assistant.\n\n"
                f"{prompt}"
            ),
        )
        return response.text.strip()
    except Exception:
        current_app.logger.exception("Gemini CV analysis request failed")
        return AI_REQUEST_FAILED_MESSAGE


def generate_cover_letter(cv_text, role_title, company, job_text, style="professional", length="standard"):
    client = _get_client()
    if client is None:
        return _placeholder_response("Cover letter generation")

    style_instructions = {
        "professional": "Use polished, direct professional language.",
        "concise": "Use especially tight, plain wording with no filler.",
        "warm": "Use a warmer personal tone while remaining professional and specific.",
    }
    length_instructions = {
        "short": "Aim for 250-300 words across 3 short body paragraphs.",
        "standard": "Aim for 300-400 words across 3-4 short body paragraphs.",
    }

    prompt = f"""
Create a concise, credible cover letter for a student or early-career applicant.

Role: {role_title}
Company: {company or "Not specified"}
Style: {style_instructions.get(style, style_instructions["professional"])}
Length: {length_instructions.get(length, length_instructions["standard"])}

Use ONLY the candidate's CV and the supplied job description.

Core rules:
- Do not invent work experience, qualifications, projects, skills, achievements,
  dates, company knowledge, awards, responsibilities, statistics, or URLs.
- If a requirement is not directly supported by the CV, use related transferable
  evidence instead of pretending the candidate has it.
- Prioritize the 2-3 strongest pieces of evidence that match the role.
- Explain why those experiences make the candidate suitable.
- Sound like a capable student or early-career professional, not a senior executive.
- Avoid generic AI phrases such as "strong interest", "results-oriented",
  "proven track record", "ever-evolving landscape", "leverage my skills",
  and repeated uses of "passionate".
- Do not repeat the same skill in multiple paragraphs.
- Do not use Markdown, headings, bullet points, square-bracket placeholders,
  explanatory comments, or labels such as "Cover Letter:".
- If the hiring manager's name is unknown, use "Dear Hiring Manager,".
- If the company address or date is unknown, leave the field empty.
- Include portfolio, LinkedIn, or GitHub only if it appears in the CV.

Return valid JSON only with this exact structure:
{{
  "candidate_name": "",
  "contact_line": "",
  "date": "",
  "recipient_name": "",
  "company": "",
  "company_location": "",
  "subject": "",
  "salutation": "",
  "opening_paragraph": "",
  "experience_paragraph": "",
  "skills_paragraph": "",
  "closing_paragraph": "",
  "sign_off": "Sincerely,",
  "candidate_name_signature": "",
  "portfolio_url": ""
}}

Use empty strings for unknown fields. Do not invent information to fill empty fields.
Before returning, silently check that the letter fits one page, contains no Markdown,
contains no placeholders, and every factual claim is supported by the CV or job
description.

CV:
{cv_text}

Job description:
{job_text}
"""

    try:
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=(
                "You write polished, truthful cover letters and return valid JSON only.\n\n"
                f"{prompt}"
            ),
        )
        return parse_cover_letter_response(response.text, role_title, company)
    except Exception:
        current_app.logger.exception("Gemini cover letter request failed")
        return AI_REQUEST_FAILED_MESSAGE


def generate_cv_tailoring_plan(cv_text, job_text, role_title="", company=""):
    client = _get_client()
    if client is None:
        return _placeholder_response("CV tailoring plan")

    prompt = f"""
Create a practical CV tailoring plan for a student or early-career applicant.

Role: {role_title or "Not specified"}
Company: {company or "Not specified"}

Use ONLY the candidate's CV and the supplied job description.

Core rules:
- Do not invent experience, qualifications, projects, metrics, employers,
  dates, certifications, responsibilities, or links.
- Do not rewrite the full CV.
- Identify what should be emphasized, reordered, clarified, or added only when
  it is already supported by the CV.
- If the job requires something not shown in the CV, label it as a gap and
  suggest a truthful way to address it.
- Keep the output specific, organized, and easy to act on.
- Avoid Markdown tables, code fences, decorative symbols, and long paragraphs.

Return clean Markdown only, using these exact headings:
## 1. Target Role Snapshot
## 2. CV Edits To Prioritize
## 3. Bullet Points To Rewrite
## 4. Skills And Keywords To Surface
## 5. Gaps To Address Honestly
## 6. Final CV Checklist

Under each heading, use 2-5 concise bullet points.

CV:
{cv_text}

Job description:
{job_text}
"""

    try:
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=(
                "You create truthful, practical CV tailoring plans. "
                "You never invent candidate evidence.\n\n"
                f"{prompt}"
            ),
        )
        return response.text.strip()
    except Exception:
        current_app.logger.exception("Gemini CV tailoring plan request failed")
        return AI_REQUEST_FAILED_MESSAGE


def generate_interview_prep(cv_text, job_text="", role_title="", company=""):
    client = _get_client()
    if client is None:
        return _placeholder_response("Interview preparation")

    prompt = f"""
Create an interview preparation plan for a student or early-career applicant.

Role: {role_title or "Not specified"}
Company: {company or "Not specified"}

Use ONLY the candidate's CV and the supplied job description if present.

Core rules:
- Do not invent experience, achievements, metrics, employers, certifications,
  projects, or responsibilities.
- Base practice stories on real CV evidence.
- If the job description is missing, make the plan general to the candidate's
  CV and clearly say it should be refined with a job description.
- Avoid Markdown tables, code fences, decorative symbols, and long paragraphs.

Return clean Markdown only, using these exact headings:
## 1. Interview Focus Areas
## 2. Likely Interview Questions
## 3. STAR Stories To Prepare
## 4. Technical Practice
## 5. Questions To Ask The Employer
## 6. Practice Schedule

Under each heading, use concise bullet points.

CV:
{cv_text}

Job description:
{job_text or "No job description provided."}
"""

    try:
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=(
                "You create truthful, practical interview preparation plans "
                "for early-career candidates.\n\n"
                f"{prompt}"
            ),
        )
        return response.text.strip()
    except Exception:
        current_app.logger.exception("Gemini interview preparation request failed")
        return AI_REQUEST_FAILED_MESSAGE


def generate_skill_gap_plan(cv_text, job_text, tracked_skills=None, role_title="", company=""):
    client = _get_client()
    if client is None:
        return _placeholder_response("Skill gap plan")

    tracked_skill_text = ", ".join(tracked_skills or []) or "None detected locally."
    prompt = f"""
Create a skill-gap plan for a student or early-career applicant.

Role: {role_title or "Not specified"}
Company: {company or "Not specified"}
Locally tracked missing skills: {tracked_skill_text}

Use ONLY the candidate's CV and the supplied job description.

Core rules:
- Do not invent existing skills, projects, certifications, or experience.
- Separate skills already demonstrated from skills that are missing or weak.
- Give practical learning steps and portfolio/project ideas that a student can
  realistically complete.
- Avoid Markdown tables, code fences, decorative symbols, and long paragraphs.

Return clean Markdown only, using these exact headings:
## 1. Priority Skill Gaps
## 2. Evidence Already Present
## 3. Learning Plan
## 4. Mini Projects To Prove The Skills
## 5. Keywords To Add Only If True
## 6. Progress Tracker

Under each heading, use concise bullet points.

CV:
{cv_text}

Job description:
{job_text}
"""

    try:
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=(
                "You create truthful skill-gap plans. You clearly separate "
                "missing skills from demonstrated evidence.\n\n"
                f"{prompt}"
            ),
        )
        return response.text.strip()
    except Exception:
        current_app.logger.exception("Gemini skill gap plan request failed")
        return AI_REQUEST_FAILED_MESSAGE


def generate_career_roadmap(cv_text, target_role="", job_text="", company=""):
    client = _get_client()
    if client is None:
        return _placeholder_response("Career roadmap")

    prompt = f"""
Create a career roadmap for a student or early-career applicant.

Target role: {target_role or "Not specified"}
Company or sector: {company or "Not specified"}

Use ONLY the candidate's CV and the supplied job description if present.

Core rules:
- Do not invent experience, achievements, certifications, or background.
- If the target role is not specified, infer sensible options from the CV but
  label them as suggestions.
- Keep the roadmap practical, staged, and measurable.
- Avoid Markdown tables, code fences, decorative symbols, and long paragraphs.

Return clean Markdown only, using these exact headings:
## 1. Best-Fit Direction
## 2. 30-Day Plan
## 3. 60-Day Plan
## 4. 90-Day Plan
## 5. Portfolio And Proof Of Work
## 6. Application Strategy

Under each heading, use concise bullet points.

CV:
{cv_text}

Job description:
{job_text or "No job description provided."}
"""

    try:
        response = client.models.generate_content(
            model=current_app.config["GEMINI_MODEL"],
            contents=(
                "You create practical early-career roadmaps grounded in the "
                "candidate's real background.\n\n"
                f"{prompt}"
            ),
        )
        return response.text.strip()
    except Exception:
        current_app.logger.exception("Gemini career roadmap request failed")
        return AI_REQUEST_FAILED_MESSAGE
