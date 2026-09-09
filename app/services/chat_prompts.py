CAREER_ASSISTANT_INSTRUCTIONS = """
You are the AI Career Assistant for a career-development platform designed for
students, graduates, and early-career professionals.

Your purpose is to help users make better career decisions and produce stronger
job applications.

Behavior:
- Be supportive, practical, and professional.
- Be conversational, context-aware, and direct. Prefer acting on supplied
  context over sounding like a workflow engine.
- Do not simply agree with the user.
- Give constructive feedback when an application, CV, experience, or strategy
  could be stronger.
- Explain why you recommend something.
- Keep ordinary conversational responses concise unless the user asks for detail.
- Ask follow-up questions only when important information is genuinely missing
  or the user's intent is genuinely ambiguous.
- Resolve references such as "the CV", "this document", "the job", "those
  roles", and "the attachment" against the supplied active CV, attached
  documents, job context, and recent conversation before asking for anything.
- Never ask the user to resend content that appears in the supplied context.
- If one document is plausible, use it. If several roles are present in one
  document and the user asks for the best fit, compare all of them.
- Treat instructions such as "don't evaluate yet" or "hold off" as an active
  constraint until the user clearly tells you to continue.
- Use concise natural acknowledgments. Do not repeatedly restate the request,
  say "standing by", or ask the user to paste supplied content.

Use of student information:
- Use supplied student context to personalize advice.
- Never invent education, experience, skills, achievements, certifications,
  employers, dates, metrics, portfolio links, or projects.
- Clearly distinguish between demonstrated skills, transferable skills, and
  required skills that are not yet demonstrated.
- If the CV context is only an excerpt, do not assume absent details are missing
  from the student's complete background.

Job applications:
- When a job description is provided, identify key requirements, compare them
  with the student's context, highlight strong matches, identify meaningful gaps,
  and recommend next actions.
- Do not claim the student has a requirement unless it is supported by the
  supplied context.

Writing style:
- Avoid generic AI phrases such as highly motivated individual,
  results-oriented professional, dynamic professional, proven track record,
  leverage my skills, and repeated uses of passionate.
- Use plain text. Do not use Markdown tables or decorative formatting.

Current limitations:
- You can advise in chat, but you cannot directly change files or submit
  applications.
- If the user wants a cover letter, ask for missing role, company, or job
  description details, then tell them to use the Generate cover letter action.
- If the user wants to tailor a CV for a role, ask for the job description if it
  is missing, then tell them to use the Create CV tailoring plan action.
- If the user wants interview practice, skill-gap planning, or a career
  roadmap, use the matching action instead of trying to fake a saved artifact in
  ordinary chat.
- If the user wants a saved job analysis, guide them to the app's Match Job
  workflow unless a tool result has been explicitly provided.
""".strip()


def build_chat_prompt(
    user_message,
    student_context,
    history_messages=None,
    job_description=None,
    conversation_context=None,
):
    history = _format_history(history_messages or [])
    context_text = student_context.get("text") or "No student context was provided."
    documents_text = "No attached documents were provided."
    active_cv_text = "No active CV was provided."
    held_instruction = ""
    if conversation_context is not None:
      active_cv = conversation_context.active_cv
      context_text = _without_repeated_cv_summary(context_text)
      if active_cv:
        active_cv_text = (
          f"Filename: {active_cv['filename']}\n"
          f"Extracted CV text:\n{active_cv['text']}"
        )
      if conversation_context.attached_documents:
        documents_text = "\n\n".join(
          (
            f"[{document.document_type}] {document.title}\n"
            f"{document.content}"
          )
          for document in conversation_context.attached_documents
          if document.document_type != "job_description"
        )
        if not documents_text:
          documents_text = "No supporting documents were provided."
      held_instruction = conversation_context.held_instruction
    job_context_text = (
        job_description.strip()
        if job_description
        else "No job description context was provided."
    )
    job_instruction = ""
    if job_description:
        job_instruction = """
When using the job description, organize fit-related answers with these short
section headings:
Fit summary
Strong matches
Gaps to address
How to position yourself
Next actions

Use short bullet lists under headings where it improves readability. Keep the
comparison grounded in the student context and job description only.
""".strip()

    return f"""
{CAREER_ASSISTANT_INSTRUCTIONS}
{job_instruction}

STUDENT CONTEXT
{context_text}

JOB DESCRIPTION CONTEXT
{job_context_text}

RECENT CONVERSATION
{history or "No previous messages in this conversation."}

CURRENT USER MESSAGE
{user_message}

ACTIVE CV
{active_cv_text}

ATTACHED / SAVED DOCUMENTS
{documents_text}

HELD USER INSTRUCTION
{held_instruction or "None"}

Reply as the career assistant. Be specific, honest, and useful.
""".strip()


def suggest_actions(user_message, reply, job_description=None):
    text = f"{user_message} {reply} {job_description or ''}".lower()
    actions = []

    if any(term in text for term in ("cover letter", "application letter")):
        actions.append("Generate cover letter")
    if (
        any(term in text for term in ("tailor", "ats", "rewrite", "optimize", "cv edit"))
        or (
            any(term in text for term in ("cv", "resume"))
            and any(term in text for term in ("job description", "role", "vacancy"))
        )
    ):
        actions.append("Create CV tailoring plan")
    if any(term in text for term in ("cv", "resume", "résumé")):
        actions.append("Review CV")
    if any(term in text for term in ("job description", "internship", "vacancy", "role")):
        actions.append("Analyze fit")
    if any(term in text for term in ("interview", "questions")):
        actions.append("Prepare interview questions")
    if any(term in text for term in ("gap", "missing", "skill")):
        actions.append("Identify skill gaps")
    if any(term in text for term in ("roadmap", "career plan", "30-day", "60-day", "90-day")):
        actions.append("Create career roadmap")

    if not actions:
        actions = ["Review CV", "Analyze fit", "Create career roadmap"]

    return actions[:4]


def _format_history(messages):
    lines = []
    for message in messages:
        role = "Student" if message.role == "user" else "Assistant"
        lines.append(f"{role}: {message.content}")
    return "\n\n".join(lines)


def _without_repeated_cv_summary(context_text):
    excluded_prefixes = (
        "Selected CV:",
        "Detected skills:",
        "Skills section:",
        "Education:",
        "Experience:",
        "Projects:",
        "Certifications:",
        "General CV evidence:",
    )
    lines = [
        line
        for line in context_text.splitlines()
        if not line.startswith(excluded_prefixes)
    ]
    return "\n".join(lines).strip() or "No additional student context was provided."
