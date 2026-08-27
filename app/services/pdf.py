from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from app.services.cover_letter import cover_letter_paragraphs, normalize_cover_letter
from app.services.text_formatting import format_text_blocks, render_inline_pdf_markup


def build_cover_letter_pdf(letter, role_title=None, company=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
    )
    styles = _cover_letter_styles()
    story = []

    if isinstance(letter, dict):
        normalized = normalize_cover_letter(letter, role_title=role_title, company=company)
    else:
        normalized = normalize_cover_letter(
            {
                "company": company,
                "subject": f"Application for {role_title}" if role_title else "",
                "salutation": "Dear Hiring Manager,",
                "opening_paragraph": str(letter or "").strip(),
            }
        )

    if normalized["candidate_name"]:
        story.append(Paragraph(escape(normalized["candidate_name"]), styles["LetterName"]))

    contact_parts = []
    if normalized["contact_line"]:
        contact_parts.append(normalized["contact_line"])
    if normalized["portfolio_url"]:
        contact_parts.append(normalized["portfolio_url"])
    if contact_parts:
        story.append(Paragraph(escape(" | ".join(contact_parts)), styles["LetterMeta"]))

    if normalized["candidate_name"] or contact_parts:
        story.append(Spacer(1, 0.2 * inch))

    for field in ("date", "recipient_name", "company", "company_location"):
        if normalized[field]:
            story.append(Paragraph(escape(normalized[field]), styles["LetterBody"]))

    if normalized["subject"]:
        story.append(Spacer(1, 0.16 * inch))
        story.append(Paragraph(escape(normalized["subject"]), styles["LetterSubject"]))

    story.append(Spacer(1, 0.16 * inch))
    story.append(Paragraph(escape(normalized["salutation"]), styles["LetterBody"]))
    story.append(Spacer(1, 0.08 * inch))

    for paragraph in cover_letter_paragraphs(normalized):
        safe_text = escape(paragraph).replace("\n", "<br/>")
        story.append(Paragraph(safe_text, styles["LetterBody"]))
        story.append(Spacer(1, 0.12 * inch))

    if normalized["sign_off"]:
        story.append(Paragraph(escape(normalized["sign_off"]), styles["LetterBody"]))
    if normalized["candidate_name_signature"]:
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(escape(normalized["candidate_name_signature"]), styles["LetterBody"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _cover_letter_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="LetterName",
            parent=styles["Title"],
            alignment=0,
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LetterMeta",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4B5563"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="LetterSubject",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LetterBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.4,
            leading=14.2,
            textColor=colors.HexColor("#111827"),
            spaceAfter=1,
        )
    )
    return styles


def build_analysis_pdf(
    analysis_text,
    role_title=None,
    company=None,
):
    return _build_structured_text_pdf(
        analysis_text,
        title_prefix="Analysis Result",
        role_title=role_title,
        company=company,
    )


def build_cv_tailoring_plan_pdf(
    plan_text,
    role_title=None,
    company=None,
):
    return _build_structured_text_pdf(
        plan_text,
        title_prefix="CV Tailoring Plan",
        role_title=role_title,
        company=company,
    )


def build_interview_prep_pdf(
    prep_text,
    role_title=None,
    company=None,
):
    return _build_structured_text_pdf(
        prep_text,
        title_prefix="Interview Preparation",
        role_title=role_title,
        company=company,
    )


def build_skill_gap_plan_pdf(
    plan_text,
    role_title=None,
    company=None,
):
    return _build_structured_text_pdf(
        plan_text,
        title_prefix="Skill Gap Plan",
        role_title=role_title,
        company=company,
    )


def build_career_roadmap_pdf(
    roadmap_text,
    role_title=None,
    company=None,
):
    return _build_structured_text_pdf(
        roadmap_text,
        title_prefix="Career Roadmap",
        role_title=role_title,
        company=company,
    )


def _build_structured_text_pdf(
    text,
    title_prefix,
    role_title=None,
    company=None,
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = _analysis_styles()
    story = []

    title = title_prefix
    if role_title:
        title = f"{title} - {role_title}"

    story.append(Paragraph(escape(title), styles["AnalysisTitle"]))

    if company:
        story.append(Paragraph(escape(f"Company: {company}"), styles["AnalysisMeta"]))

    story.append(Spacer(1, 0.2 * inch))

    for block in format_text_blocks(text):
        if block["kind"] == "heading":
            story.append(Paragraph(render_inline_pdf_markup(block["content"]), styles["AnalysisHeading"]))
            story.append(Spacer(1, 0.08 * inch))
        elif block["kind"] in {"list", "ordered_list"}:
            items = [
                ListItem(
                    Paragraph(render_inline_pdf_markup(item), styles["AnalysisBody"]),
                    leftIndent=8,
                )
                for item in block["entries"]
            ]
            story.append(
                ListFlowable(
                    items,
                    bulletType="1" if block["kind"] == "ordered_list" else "bullet",
                    leftIndent=16,
                    bulletFontName="Helvetica",
                    bulletFontSize=8,
                    bulletColor=colors.HexColor("#3B82F6"),
                )
            )
            story.append(Spacer(1, 0.12 * inch))
        else:
            story.append(Paragraph(render_inline_pdf_markup(block["content"]), styles["AnalysisBody"]))
            story.append(Spacer(1, 0.12 * inch))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _analysis_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="AnalysisTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AnalysisMeta",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AnalysisHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AnalysisBody",
            parent=styles["BodyText"],
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        )
    )
    return styles
