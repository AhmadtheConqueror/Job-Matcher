import json
from pathlib import Path
from uuid import uuid4

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.models import (
    AnalysisResult,
    CV,
    ChatConversation,
    ChatConversationContext,
    ChatFeedback,
    ChatMessage,
    JobDescription,
    SkillGap,
    utc_now,
)
from app.services.ai import (
    analyze_cv_against_job,
    generate_career_roadmap,
    generate_cover_letter,
    generate_cv_tailoring_plan,
    generate_interview_prep,
    generate_skill_gap_plan,
    is_ai_error_response,
)
from app.services.cover_letter import (
    LENGTH_OPTIONS,
    STYLE_OPTIONS,
    cover_letter_to_text,
    deserialize_cover_letter,
    normalize_cover_letter,
    serialize_cover_letter,
)
from app.services.cv_parser import extract_text_from_file
from app.services.chatbot import generate_chat_reply
from app.services.evaluation import (
    build_anonymized_training_jsonl,
    build_evaluation_dashboard,
)
from app.services.pdf import (
    build_analysis_pdf,
    build_career_roadmap_pdf,
    build_cover_letter_pdf,
    build_cv_tailoring_plan_pdf,
    build_interview_prep_pdf,
    build_skill_gap_plan_pdf,
)
from app.services.prompt_versions import prompt_version
from app.services.skill_gap_tracker import (
    SKILL_GAP_PRIORITIES,
    SKILL_GAP_STATUSES,
    serialize_skill_gap,
    track_skill_gaps_from_text,
)
from app.services.student_context import context_status_for_user
from app.services.text_formatting import format_text_blocks

main_bp = Blueprint("main", __name__)
MAX_CHAT_JOB_DESCRIPTION_LENGTH = 12000


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    cvs = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .limit(5)
        .all()
    )
    analyses = (
        AnalysisResult.query.filter_by(user_id=current_user.id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template("dashboard.html", cvs=cvs, analyses=analyses)


@main_bp.route("/evaluations")
@login_required
def evaluations():
    dashboard_data = build_evaluation_dashboard(current_user)
    return render_template("evaluations.html", dashboard=dashboard_data)


@main_bp.route("/evaluations/training-data.jsonl")
@login_required
def download_training_data():
    jsonl = build_anonymized_training_jsonl(current_user)
    return Response(
        jsonl,
        mimetype="application/jsonl",
        headers={
            "Content-Disposition": "attachment; filename=training-data.jsonl",
        },
    )


@main_bp.route("/chat")
@login_required
def chat():
    return render_template(
        "chat.html",
        style_options=STYLE_OPTIONS,
        length_options=LENGTH_OPTIONS,
    )


@main_bp.route("/api/chat/conversations", methods=["GET"])
@login_required
def chat_conversations():
    conversations = (
        ChatConversation.query.filter_by(user_id=current_user.id)
        .order_by(ChatConversation.updated_at.desc())
        .limit(30)
        .all()
    )
    return jsonify(
        {
            "conversations": [
                _serialize_conversation(conversation)
                for conversation in conversations
            ]
        }
    )


@main_bp.route("/api/chat/context", methods=["GET"])
@login_required
def chat_context_status():
    return jsonify(context_status_for_user(current_user))


@main_bp.route("/api/skill-gaps", methods=["GET"])
@login_required
def skill_gaps():
    records = (
        SkillGap.query.filter_by(user_id=current_user.id)
        .order_by(SkillGap.updated_at.desc())
        .all()
    )
    return jsonify({"skill_gaps": [serialize_skill_gap(record) for record in records]})


@main_bp.route("/api/skill-gaps/<int:gap_id>", methods=["PATCH"])
@login_required
def update_skill_gap(gap_id):
    data = request.get_json(silent=True) or {}
    record = SkillGap.query.filter_by(
        id=gap_id,
        user_id=current_user.id,
    ).first_or_404()

    status = (data.get("status") or record.status).strip()
    priority = (data.get("priority") or record.priority).strip()
    notes = data.get("notes")

    if status not in SKILL_GAP_STATUSES:
        return jsonify({"error": "Choose a valid skill status."}), 400
    if priority not in SKILL_GAP_PRIORITIES:
        return jsonify({"error": "Choose a valid skill priority."}), 400

    record.status = status
    record.priority = priority
    if notes is not None:
        record.notes = str(notes).strip()
    record.updated_at = utc_now()
    db.session.add(record)
    db.session.commit()

    return jsonify({"skill_gap": serialize_skill_gap(record)})


@main_bp.route("/api/chat/conversations", methods=["POST"])
@login_required
def create_chat_conversation():
    conversation = ChatConversation(user_id=current_user.id, title="New chat")
    db.session.add(conversation)
    db.session.commit()
    return jsonify({"conversation": _serialize_conversation(conversation)}), 201


@main_bp.route("/api/chat/conversations/<int:conversation_id>", methods=["GET"])
@login_required
def chat_conversation_detail(conversation_id):
    conversation = ChatConversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id,
    ).first_or_404()
    messages = (
        ChatMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "messages": [_serialize_message(message) for message in messages],
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
        }
    )


@main_bp.route("/api/chat/conversations/<int:conversation_id>", methods=["DELETE"])
@login_required
def delete_chat_conversation(conversation_id):
    conversation = ChatConversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id,
    ).first()

    if conversation is None:
        return jsonify({"error": "Conversation not found."}), 404

    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"ok": True})


@main_bp.route("/api/chat", methods=["POST"])
@login_required
def post_chat_message():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")
    include_latest_cv = bool(data.get("include_latest_cv", True))
    try:
        cv_id = int(data["cv_id"]) if data.get("cv_id") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Selected CV was not found."}), 400
    has_job_description_input = "job_description" in data
    job_description = (data.get("job_description") or "").strip()

    if cv_id and not CV.query.filter_by(id=cv_id, user_id=current_user.id).first():
        return jsonify({"error": "Selected CV was not found."}), 404

    if not user_message:
        return jsonify({"error": "Write a message before sending."}), 400
    if len(user_message) > 8000:
        return jsonify({"error": "Keep each message under 8,000 characters."}), 400
    if len(job_description) > MAX_CHAT_JOB_DESCRIPTION_LENGTH:
        return jsonify(
            {
                "error": (
                    "Keep the job description under "
                    f"{MAX_CHAT_JOB_DESCRIPTION_LENGTH:,} characters."
                )
            }
        ), 400

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
        ).first()
        if conversation is None:
            return jsonify({"error": "Conversation not found."}), 404
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_chat_title_from_message(user_message),
        )
        db.session.add(conversation)
        db.session.flush()

    if has_job_description_input:
        if job_description:
            _upsert_chat_context(
                conversation,
                kind="job_description",
                title="Job description",
                content=job_description,
            )
        else:
            _delete_chat_context(conversation, kind="job_description")

    active_job_context = _get_chat_context(conversation, kind="job_description")
    active_job_description = active_job_context.content if active_job_context else ""

    history = (
        ChatMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(8)
        .all()
    )
    history = list(reversed(history))

    if conversation.title == "New chat":
        conversation.title = _chat_title_from_message(user_message)

    user_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=user_message,
    )
    conversation.updated_at = utc_now()
    db.session.add(user_record)
    db.session.commit()

    result = generate_chat_reply(
        current_user,
        conversation,
        user_message,
        include_latest_cv=include_latest_cv,
        cv_id=cv_id,
        history=history,
        job_description=active_job_description,
    )
    reply = result["reply"]
    if is_ai_error_response(reply):
        return jsonify(
            {
                "error": reply,
                "conversation": _serialize_conversation(conversation),
                "job_context": _serialize_chat_job_context(
                    conversation,
                    include_content=True,
                ),
            }
        ), 502

    tracked_skill_gaps = []
    if (
        active_job_description
        and _chat_requests_skill_gap_tracking(user_message)
    ):
        latest_cv = _selected_chat_cv(cv_id)
        if latest_cv is not None:
            tracked_skill_gaps = track_skill_gaps_from_text(
                current_user.id,
                latest_cv.text,
                active_job_description,
                source="Chat skill gap discussion",
            )

    assistant_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=reply,
        metadata_json=json.dumps(
            {
                "suggested_actions": result["suggested_actions"],
                "include_latest_cv": include_latest_cv,
                "used_latest_cv": result["used_latest_cv"],
                "latest_cv_filename": result["latest_cv_filename"],
                "detected_skills": result["detected_skills"],
                "used_job_description": result["used_job_description"],
                "job_description_excerpt": result["job_description_excerpt"],
                "prompt_version": result["prompt_version"],
                "provider": result["provider"],
                "tracked_skill_gaps": [
                    gap.skill for gap in tracked_skill_gaps
                ],
            }
        ),
    )
    conversation.updated_at = utc_now()
    db.session.add(assistant_record)
    db.session.commit()

    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "user_message": _serialize_message(user_record),
            "assistant_message": _serialize_message(assistant_record),
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
            "reply": reply,
            "suggested_actions": result["suggested_actions"],
            "used_latest_cv": result["used_latest_cv"],
            "latest_cv_filename": result["latest_cv_filename"],
            "detected_skills": result["detected_skills"],
            "used_job_description": result["used_job_description"],
            "job_description_excerpt": result["job_description_excerpt"],
            "skill_gaps": [
                serialize_skill_gap(gap) for gap in tracked_skill_gaps
            ],
        }
    )


@main_bp.route("/api/chat/actions/cover-letter", methods=["POST"])
@login_required
def chat_cover_letter_action():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    role_title = (data.get("role_title") or "").strip()
    company = (data.get("company") or "").strip()
    selected_style = data.get("letter_style", "professional")
    selected_length = data.get("letter_length", "standard")
    has_job_description_input = "job_description" in data
    job_description = (data.get("job_description") or "").strip()

    if selected_style not in STYLE_OPTIONS:
        selected_style = "professional"
    if selected_length not in LENGTH_OPTIONS:
        selected_length = "standard"
    if len(job_description) > MAX_CHAT_JOB_DESCRIPTION_LENGTH:
        return jsonify(
            {
                "error": (
                    "Keep the job description under "
                    f"{MAX_CHAT_JOB_DESCRIPTION_LENGTH:,} characters."
                )
            }
        ), 400

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
        ).first()
        if conversation is None:
            return jsonify({"error": "Conversation not found."}), 404
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_chat_title_from_message("Generate cover letter"),
        )
        db.session.add(conversation)
        db.session.flush()

    if has_job_description_input:
        if job_description:
            _upsert_chat_context(
                conversation,
                kind="job_description",
                title="Job description",
                content=job_description,
            )
        else:
            _delete_chat_context(conversation, kind="job_description")

    active_job_context = _get_chat_context(conversation, kind="job_description")
    active_job_description = active_job_context.content if active_job_context else ""
    latest_cv = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    if latest_cv is None:
        return jsonify({"error": "Upload a CV before generating a cover letter."}), 400
    if not role_title:
        return jsonify({"error": "Add the role title before generating a cover letter."}), 400
    if not active_job_description:
        return jsonify(
            {"error": "Paste a job description before generating a cover letter."}
        ), 400

    action_text = f"Generate a cover letter for {role_title}"
    if company:
        action_text = f"{action_text} at {company}"
    action_text = f"{action_text}."

    user_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=action_text,
    )
    conversation.updated_at = utc_now()
    db.session.add(user_record)
    db.session.commit()

    generated_letter = generate_cover_letter(
        latest_cv.text,
        role_title,
        company,
        active_job_description,
        style=selected_style,
        length=selected_length,
    )
    if is_ai_error_response(generated_letter):
        return jsonify(
            {
                "error": generated_letter,
                "conversation": _serialize_conversation(conversation),
                "user_message": _serialize_message(user_record),
                "job_context": _serialize_chat_job_context(
                    conversation,
                    include_content=True,
                ),
            }
        ), 502
    if not isinstance(generated_letter, dict):
        return jsonify(
            {
                "error": "The cover-letter generator returned an invalid draft.",
                "conversation": _serialize_conversation(conversation),
                "user_message": _serialize_message(user_record),
            }
        ), 502

    generated_letter = normalize_cover_letter(
        generated_letter,
        role_title=role_title,
        company=company,
    )
    letter_payload = serialize_cover_letter(generated_letter)
    letter_text = cover_letter_to_text(generated_letter)

    assistant_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=letter_text,
        metadata_json=json.dumps(
            {
                "suggested_actions": [
                    "Make this cover letter shorter",
                    "Make it more specific",
                    "Prepare interview questions",
                ],
                "tool_action": "cover_letter",
                "cover_letter_payload": letter_payload,
                "role_title": role_title,
                "company": company,
                "letter_style": selected_style,
                "letter_length": selected_length,
                "latest_cv_filename": latest_cv.original_filename,
                "used_latest_cv": True,
                "used_job_description": True,
                "job_description_excerpt": _text_excerpt(
                    active_job_description,
                    limit=180,
                ),
                "prompt_version": prompt_version("cover_letter"),
                "provider": current_app.config.get("AI_PROVIDER", "gemini"),
            }
        ),
    )
    conversation.updated_at = utc_now()
    db.session.add(assistant_record)
    db.session.commit()

    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "user_message": _serialize_message(user_record),
            "assistant_message": _serialize_message(assistant_record),
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
        }
    )


@main_bp.route("/api/chat/messages/<int:message_id>/cover-letter/download")
@login_required
def download_chat_cover_letter(message_id):
    message = (
        ChatMessage.query.join(ChatConversation)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.role == "assistant",
            ChatConversation.user_id == current_user.id,
        )
        .first_or_404()
    )
    metadata = _message_metadata(message)

    if metadata.get("tool_action") != "cover_letter":
        abort(404)

    letter_payload = metadata.get("cover_letter_payload", "")
    letter = deserialize_cover_letter(letter_payload) if letter_payload else message.content
    role_title = metadata.get("role_title", "")
    company = metadata.get("company", "")
    pdf = build_cover_letter_pdf(letter, role_title, company)

    filename_parts = ["cover-letter"]
    if role_title:
        filename_parts.append(secure_filename(role_title.lower()) or "role")
    download_name = "-".join(filename_parts) + ".pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@main_bp.route("/api/chat/actions/cv-tailoring-plan", methods=["POST"])
@login_required
def chat_cv_tailoring_plan_action():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    role_title = (data.get("role_title") or "").strip()
    company = (data.get("company") or "").strip()
    has_job_description_input = "job_description" in data
    job_description = (data.get("job_description") or "").strip()

    if len(job_description) > MAX_CHAT_JOB_DESCRIPTION_LENGTH:
        return jsonify(
            {
                "error": (
                    "Keep the job description under "
                    f"{MAX_CHAT_JOB_DESCRIPTION_LENGTH:,} characters."
                )
            }
        ), 400

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
        ).first()
        if conversation is None:
            return jsonify({"error": "Conversation not found."}), 404
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_chat_title_from_message("Create CV tailoring plan"),
        )
        db.session.add(conversation)
        db.session.flush()

    if has_job_description_input:
        if job_description:
            _upsert_chat_context(
                conversation,
                kind="job_description",
                title="Job description",
                content=job_description,
            )
        else:
            _delete_chat_context(conversation, kind="job_description")

    active_job_context = _get_chat_context(conversation, kind="job_description")
    active_job_description = active_job_context.content if active_job_context else ""
    latest_cv = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    if latest_cv is None:
        return jsonify({"error": "Upload a CV before creating a CV plan."}), 400
    if not active_job_description:
        return jsonify({"error": "Paste a job description before creating a CV plan."}), 400

    action_text = "Create a CV tailoring plan"
    if role_title:
        action_text = f"{action_text} for {role_title}"
    if company:
        action_text = f"{action_text} at {company}"
    action_text = f"{action_text}."

    user_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=action_text,
    )
    conversation.updated_at = utc_now()
    db.session.add(user_record)
    db.session.commit()

    plan_text = generate_cv_tailoring_plan(
        latest_cv.text,
        active_job_description,
        role_title=role_title,
        company=company,
    )
    if is_ai_error_response(plan_text):
        return jsonify(
            {
                "error": plan_text,
                "conversation": _serialize_conversation(conversation),
                "user_message": _serialize_message(user_record),
                "job_context": _serialize_chat_job_context(
                    conversation,
                    include_content=True,
                ),
            }
        ), 502

    assistant_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=plan_text,
        metadata_json=json.dumps(
            {
                "suggested_actions": [
                    "Generate cover letter",
                    "Make this plan more detailed",
                    "Prepare interview questions",
                ],
                "tool_action": "cv_tailoring_plan",
                "role_title": role_title,
                "company": company,
                "latest_cv_filename": latest_cv.original_filename,
                "used_latest_cv": True,
                "used_job_description": True,
                "job_description_excerpt": _text_excerpt(
                    active_job_description,
                    limit=180,
                ),
                "prompt_version": prompt_version("cv_tailoring_plan"),
                "provider": current_app.config.get("AI_PROVIDER", "gemini"),
            }
        ),
    )
    conversation.updated_at = utc_now()
    db.session.add(assistant_record)
    db.session.commit()

    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "user_message": _serialize_message(user_record),
            "assistant_message": _serialize_message(assistant_record),
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
        }
    )


@main_bp.route("/api/chat/messages/<int:message_id>/cv-tailoring-plan/download")
@login_required
def download_chat_cv_tailoring_plan(message_id):
    message = (
        ChatMessage.query.join(ChatConversation)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.role == "assistant",
            ChatConversation.user_id == current_user.id,
        )
        .first_or_404()
    )
    metadata = _message_metadata(message)

    if metadata.get("tool_action") != "cv_tailoring_plan":
        abort(404)

    pdf = build_cv_tailoring_plan_pdf(
        message.content,
        role_title=metadata.get("role_title", ""),
        company=metadata.get("company", ""),
    )
    filename_parts = ["cv-tailoring-plan"]
    if metadata.get("role_title"):
        filename_parts.append(
            secure_filename(metadata["role_title"].lower()) or "role"
        )
    download_name = "-".join(filename_parts) + ".pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@main_bp.route("/api/chat/actions/interview-prep", methods=["POST"])
@login_required
def chat_interview_prep_action():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    role_title = (data.get("role_title") or "").strip()
    company = (data.get("company") or "").strip()
    has_job_description_input = "job_description" in data
    job_description = (data.get("job_description") or "").strip()

    if len(job_description) > MAX_CHAT_JOB_DESCRIPTION_LENGTH:
        return jsonify(
            {
                "error": (
                    "Keep the job description under "
                    f"{MAX_CHAT_JOB_DESCRIPTION_LENGTH:,} characters."
                )
            }
        ), 400

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
        ).first()
        if conversation is None:
            return jsonify({"error": "Conversation not found."}), 404
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_chat_title_from_message("Prepare interview questions"),
        )
        db.session.add(conversation)
        db.session.flush()

    if has_job_description_input:
        if job_description:
            _upsert_chat_context(
                conversation,
                kind="job_description",
                title="Job description",
                content=job_description,
            )
        else:
            _delete_chat_context(conversation, kind="job_description")

    active_job_context = _get_chat_context(conversation, kind="job_description")
    active_job_description = active_job_context.content if active_job_context else ""
    latest_cv = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    if latest_cv is None:
        return jsonify({"error": "Upload a CV before preparing interviews."}), 400

    action_text = "Prepare interview questions"
    if role_title:
        action_text = f"{action_text} for {role_title}"
    if company:
        action_text = f"{action_text} at {company}"
    action_text = f"{action_text}."

    user_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=action_text,
    )
    conversation.updated_at = utc_now()
    db.session.add(user_record)
    db.session.commit()

    prep_text = generate_interview_prep(
        latest_cv.text,
        active_job_description,
        role_title=role_title,
        company=company,
    )
    if is_ai_error_response(prep_text):
        return jsonify(
            {
                "error": prep_text,
                "conversation": _serialize_conversation(conversation),
                "user_message": _serialize_message(user_record),
                "job_context": _serialize_chat_job_context(
                    conversation,
                    include_content=True,
                ),
            }
        ), 502

    assistant_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=prep_text,
        metadata_json=json.dumps(
            {
                "suggested_actions": [
                    "Identify skill gaps",
                    "Create CV tailoring plan",
                    "Generate cover letter",
                ],
                "tool_action": "interview_prep",
                "role_title": role_title,
                "company": company,
                "latest_cv_filename": latest_cv.original_filename,
                "used_latest_cv": True,
                "used_job_description": bool(active_job_description),
                "job_description_excerpt": _text_excerpt(
                    active_job_description,
                    limit=180,
                ),
                "prompt_version": prompt_version("interview_prep"),
                "provider": current_app.config.get("AI_PROVIDER", "gemini"),
            }
        ),
    )
    conversation.updated_at = utc_now()
    db.session.add(assistant_record)
    db.session.commit()

    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "user_message": _serialize_message(user_record),
            "assistant_message": _serialize_message(assistant_record),
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
        }
    )


@main_bp.route("/api/chat/actions/skill-gap-plan", methods=["POST"])
@login_required
def chat_skill_gap_plan_action():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    role_title = (data.get("role_title") or "").strip()
    company = (data.get("company") or "").strip()
    has_job_description_input = "job_description" in data
    job_description = (data.get("job_description") or "").strip()

    if len(job_description) > MAX_CHAT_JOB_DESCRIPTION_LENGTH:
        return jsonify(
            {
                "error": (
                    "Keep the job description under "
                    f"{MAX_CHAT_JOB_DESCRIPTION_LENGTH:,} characters."
                )
            }
        ), 400

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
        ).first()
        if conversation is None:
            return jsonify({"error": "Conversation not found."}), 404
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_chat_title_from_message("Identify skill gaps"),
        )
        db.session.add(conversation)
        db.session.flush()

    if has_job_description_input:
        if job_description:
            _upsert_chat_context(
                conversation,
                kind="job_description",
                title="Job description",
                content=job_description,
            )
        else:
            _delete_chat_context(conversation, kind="job_description")

    active_job_context = _get_chat_context(conversation, kind="job_description")
    active_job_description = active_job_context.content if active_job_context else ""
    latest_cv = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    if latest_cv is None:
        return jsonify({"error": "Upload a CV before tracking skill gaps."}), 400
    if not active_job_description:
        return jsonify({"error": "Paste a job description before tracking skill gaps."}), 400

    action_text = "Identify skill gaps"
    if role_title:
        action_text = f"{action_text} for {role_title}"
    if company:
        action_text = f"{action_text} at {company}"
    action_text = f"{action_text}."

    user_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=action_text,
    )
    conversation.updated_at = utc_now()
    db.session.add(user_record)
    db.session.commit()

    tracked_gaps = track_skill_gaps_from_text(
        current_user.id,
        latest_cv.text,
        active_job_description,
        source="Chat skill gap plan",
    )
    plan_text = generate_skill_gap_plan(
        latest_cv.text,
        active_job_description,
        tracked_skills=[gap.skill for gap in tracked_gaps],
        role_title=role_title,
        company=company,
    )
    if is_ai_error_response(plan_text):
        db.session.rollback()
        return jsonify(
            {
                "error": plan_text,
                "conversation": _serialize_conversation(conversation),
                "user_message": _serialize_message(user_record),
                "job_context": _serialize_chat_job_context(
                    conversation,
                    include_content=True,
                ),
            }
        ), 502

    db.session.flush()
    assistant_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=plan_text,
        metadata_json=json.dumps(
            {
                "suggested_actions": [
                    "Create CV tailoring plan",
                    "Prepare interview questions",
                    "Create career roadmap",
                ],
                "tool_action": "skill_gap_plan",
                "role_title": role_title,
                "company": company,
                "tracked_skills": [
                    serialize_skill_gap(gap)
                    for gap in tracked_gaps
                ],
                "latest_cv_filename": latest_cv.original_filename,
                "used_latest_cv": True,
                "used_job_description": True,
                "job_description_excerpt": _text_excerpt(
                    active_job_description,
                    limit=180,
                ),
                "prompt_version": prompt_version("skill_gap_plan"),
                "provider": current_app.config.get("AI_PROVIDER", "gemini"),
            }
        ),
    )
    conversation.updated_at = utc_now()
    db.session.add(assistant_record)
    db.session.commit()

    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "user_message": _serialize_message(user_record),
            "assistant_message": _serialize_message(assistant_record),
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
            "skill_gaps": [
                serialize_skill_gap(gap)
                for gap in tracked_gaps
            ],
        }
    )


@main_bp.route("/api/chat/actions/career-roadmap", methods=["POST"])
@login_required
def chat_career_roadmap_action():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    target_role = (data.get("target_role") or data.get("role_title") or "").strip()
    company = (data.get("company") or "").strip()
    has_job_description_input = "job_description" in data
    job_description = (data.get("job_description") or "").strip()

    if len(job_description) > MAX_CHAT_JOB_DESCRIPTION_LENGTH:
        return jsonify(
            {
                "error": (
                    "Keep the job description under "
                    f"{MAX_CHAT_JOB_DESCRIPTION_LENGTH:,} characters."
                )
            }
        ), 400

    if conversation_id:
        conversation = ChatConversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
        ).first()
        if conversation is None:
            return jsonify({"error": "Conversation not found."}), 404
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_chat_title_from_message("Create career roadmap"),
        )
        db.session.add(conversation)
        db.session.flush()

    if has_job_description_input:
        if job_description:
            _upsert_chat_context(
                conversation,
                kind="job_description",
                title="Job description",
                content=job_description,
            )
        else:
            _delete_chat_context(conversation, kind="job_description")

    active_job_context = _get_chat_context(conversation, kind="job_description")
    active_job_description = active_job_context.content if active_job_context else ""
    latest_cv = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )

    if latest_cv is None:
        return jsonify({"error": "Upload a CV before creating a roadmap."}), 400

    action_text = "Create a career roadmap"
    if target_role:
        action_text = f"{action_text} for {target_role}"
    if company:
        action_text = f"{action_text} at {company}"
    action_text = f"{action_text}."

    user_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=action_text,
    )
    conversation.updated_at = utc_now()
    db.session.add(user_record)
    db.session.commit()

    roadmap_text = generate_career_roadmap(
        latest_cv.text,
        target_role=target_role,
        job_text=active_job_description,
        company=company,
    )
    if is_ai_error_response(roadmap_text):
        return jsonify(
            {
                "error": roadmap_text,
                "conversation": _serialize_conversation(conversation),
                "user_message": _serialize_message(user_record),
                "job_context": _serialize_chat_job_context(
                    conversation,
                    include_content=True,
                ),
            }
        ), 502

    assistant_record = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="assistant",
        content=roadmap_text,
        metadata_json=json.dumps(
            {
                "suggested_actions": [
                    "Identify skill gaps",
                    "Create CV tailoring plan",
                    "Prepare interview questions",
                ],
                "tool_action": "career_roadmap",
                "role_title": target_role,
                "company": company,
                "latest_cv_filename": latest_cv.original_filename,
                "used_latest_cv": True,
                "used_job_description": bool(active_job_description),
                "job_description_excerpt": _text_excerpt(
                    active_job_description,
                    limit=180,
                ),
                "prompt_version": prompt_version("career_roadmap"),
                "provider": current_app.config.get("AI_PROVIDER", "gemini"),
            }
        ),
    )
    conversation.updated_at = utc_now()
    db.session.add(assistant_record)
    db.session.commit()

    return jsonify(
        {
            "conversation": _serialize_conversation(conversation),
            "user_message": _serialize_message(user_record),
            "assistant_message": _serialize_message(assistant_record),
            "job_context": _serialize_chat_job_context(
                conversation,
                include_content=True,
            ),
        }
    )


@main_bp.route("/api/chat/messages/<int:message_id>/interview-prep/download")
@login_required
def download_chat_interview_prep(message_id):
    message = _chat_tool_message_or_404(message_id, "interview_prep")
    metadata = _message_metadata(message)
    pdf = build_interview_prep_pdf(
        message.content,
        role_title=metadata.get("role_title", ""),
        company=metadata.get("company", ""),
    )
    return _send_chat_artifact_pdf(pdf, "interview-prep", metadata.get("role_title", ""))


@main_bp.route("/api/chat/messages/<int:message_id>/skill-gap-plan/download")
@login_required
def download_chat_skill_gap_plan(message_id):
    message = _chat_tool_message_or_404(message_id, "skill_gap_plan")
    metadata = _message_metadata(message)
    pdf = build_skill_gap_plan_pdf(
        message.content,
        role_title=metadata.get("role_title", ""),
        company=metadata.get("company", ""),
    )
    return _send_chat_artifact_pdf(pdf, "skill-gap-plan", metadata.get("role_title", ""))


@main_bp.route("/api/chat/messages/<int:message_id>/career-roadmap/download")
@login_required
def download_chat_career_roadmap(message_id):
    message = _chat_tool_message_or_404(message_id, "career_roadmap")
    metadata = _message_metadata(message)
    pdf = build_career_roadmap_pdf(
        message.content,
        role_title=metadata.get("role_title", ""),
        company=metadata.get("company", ""),
    )
    return _send_chat_artifact_pdf(pdf, "career-roadmap", metadata.get("role_title", ""))


@main_bp.route("/api/chat/messages/<int:message_id>/feedback", methods=["POST"])
@login_required
def chat_message_feedback(message_id):
    data = request.get_json(silent=True) or {}
    rating = (data.get("rating") or "").strip()
    note = (data.get("note") or "").strip()
    allowed_ratings = {
        "helpful",
        "not_helpful",
        "too_generic",
        "invented_fact",
        "too_long",
        "bad_formatting",
        "wrong_tone",
        "excellent",
    }

    if rating not in allowed_ratings:
        return jsonify({"error": "Choose a valid feedback rating."}), 400

    message = (
        ChatMessage.query.join(ChatConversation)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.role == "assistant",
            ChatConversation.user_id == current_user.id,
        )
        .first()
    )
    if message is None:
        return jsonify({"error": "Message not found."}), 404

    feedback = ChatFeedback.query.filter_by(
        message_id=message.id,
        user_id=current_user.id,
    ).first()
    if feedback is None:
        feedback = ChatFeedback(
            message_id=message.id,
            user_id=current_user.id,
            rating=rating,
            note=note,
        )
        db.session.add(feedback)
    else:
        feedback.rating = rating
        feedback.note = note
        feedback.created_at = utc_now()

    db.session.commit()
    return jsonify({"ok": True, "rating": feedback.rating})


@main_bp.route("/cv/upload", methods=["GET", "POST"])
@login_required
def upload_cv():
    if request.method == "POST":
        uploaded = request.files.get("cv_file")
        if not uploaded or uploaded.filename == "":
            flash("Choose a PDF, DOCX, or TXT file.", "danger")
            return redirect(url_for("main.upload_cv"))

        extension = uploaded.filename.rsplit(".", 1)[-1].lower()
        if extension not in current_app.config["ALLOWED_CV_EXTENSIONS"]:
            flash("Unsupported file type. Upload PDF, DOCX, or TXT.", "danger")
            return redirect(url_for("main.upload_cv"))

        safe_name = secure_filename(uploaded.filename)
        stored_name = f"{uuid4().hex}_{safe_name}"
        destination = Path(current_app.config["UPLOAD_FOLDER"]) / stored_name
        uploaded.save(destination)

        try:
            text = extract_text_from_file(destination)
        except ValueError as exc:
            destination.unlink(missing_ok=True)
            flash(str(exc), "danger")
            return redirect(url_for("main.upload_cv"))

        cv = CV(
            user_id=current_user.id,
            filename=stored_name,
            original_filename=safe_name,
            text=text,
        )
        db.session.add(cv)
        db.session.commit()
        flash("CV uploaded and parsed.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("cv_upload.html")


@main_bp.route("/cv/<int:cv_id>/delete", methods=["POST"])
@login_required
def delete_cv(cv_id):
    cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first_or_404()
    file_path = Path(current_app.config["UPLOAD_FOLDER"]) / cv.filename
    db.session.delete(cv)
    db.session.commit()
    file_path.unlink(missing_ok=True)
    flash("CV deleted.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/match", methods=["GET", "POST"])
@login_required
def match_job():
    cvs = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .all()
    )

    if request.method == "POST":
        cv_id = request.form.get("cv_id", type=int)
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        description = request.form.get("description", "").strip()

        cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
        if not cv or not title or not description:
            flash("Choose a CV and add the job title and description.", "danger")
            return render_template("match.html", cvs=cvs)

        job = JobDescription(
            user_id=current_user.id,
            title=title,
            company=company,
            description=description,
        )
        db.session.add(job)
        db.session.flush()

        result_text = analyze_cv_against_job(cv.text, description)
        if is_ai_error_response(result_text):
            db.session.rollback()
            flash(result_text, "danger")
            return render_template("match.html", cvs=cvs)

        analysis = AnalysisResult(
            user_id=current_user.id,
            cv_id=cv.id,
            job_description_id=job.id,
            result_text=result_text,
        )
        db.session.add(analysis)
        db.session.commit()
        flash("Analysis complete.", "success")
        return redirect(url_for("main.result_detail", result_id=analysis.id))

    return render_template("match.html", cvs=cvs)


@main_bp.route("/results/<int:result_id>")
@login_required
def result_detail(result_id):
    result = AnalysisResult.query.filter_by(
        id=result_id, user_id=current_user.id
    ).first_or_404()
    return render_template(
        "result.html",
        result=result,
        result_blocks=format_text_blocks(result.result_text),
    )


@main_bp.route("/results/<int:result_id>/download")
@login_required
def download_result_pdf(result_id):
    result = AnalysisResult.query.filter_by(
        id=result_id, user_id=current_user.id
    ).first_or_404()

    pdf = build_analysis_pdf(
        result.result_text,
        role_title=result.job_description.title,
        company=result.job_description.company,
    )
    filename_parts = ["analysis-result"]
    if result.job_description.title:
        filename_parts.append(secure_filename(result.job_description.title.lower()) or "role")
    download_name = "-".join(filename_parts) + ".pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@main_bp.route("/cover-letter", methods=["GET", "POST"])
@login_required
def cover_letter():
    cvs = (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .all()
    )
    generated_letter = None
    letter_payload = ""
    letter_text = ""
    role_title = ""
    company = ""
    selected_style = "professional"
    selected_length = "standard"

    if request.method == "POST":
        cv_id = request.form.get("cv_id", type=int)
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        description = request.form.get("description", "").strip()
        selected_style = request.form.get("letter_style", selected_style)
        selected_length = request.form.get("letter_length", selected_length)
        cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
        role_title = title

        if not cv or not title or not description:
            flash("Choose a CV and add the role details.", "danger")
        else:
            generated_letter = generate_cover_letter(
                cv.text,
                title,
                company,
                description,
                style=selected_style,
                length=selected_length,
            )
            if is_ai_error_response(generated_letter):
                flash(generated_letter, "danger")
                generated_letter = None
            elif not isinstance(generated_letter, dict):
                flash(generated_letter, "warning")
                generated_letter = None
            else:
                generated_letter = normalize_cover_letter(
                    generated_letter,
                    role_title=role_title,
                    company=company,
                )
                letter_payload = serialize_cover_letter(generated_letter)
                letter_text = cover_letter_to_text(generated_letter)

    return render_template(
        "cover_letter.html",
        cvs=cvs,
        generated_letter=generated_letter,
        letter_payload=letter_payload,
        letter_text=letter_text,
        role_title=role_title,
        company=company,
        style_options=STYLE_OPTIONS,
        length_options=LENGTH_OPTIONS,
        selected_style=selected_style,
        selected_length=selected_length,
    )


@main_bp.route("/cover-letter/download", methods=["POST"])
@login_required
def download_cover_letter():
    letter_payload = request.form.get("letter_payload", "").strip()
    letter_text = request.form.get("letter_text", "").strip()
    role_title = request.form.get("role_title", "").strip()
    company = request.form.get("company", "").strip()

    if not letter_payload and not letter_text:
        flash("Generate a cover letter before downloading the PDF.", "warning")
        return redirect(url_for("main.cover_letter"))

    letter = deserialize_cover_letter(letter_payload) if letter_payload else letter_text
    pdf = build_cover_letter_pdf(letter, role_title, company)
    filename_parts = ["cover-letter"]
    if role_title:
        filename_parts.append(secure_filename(role_title.lower()) or "role")
    download_name = "-".join(filename_parts) + ".pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


def _serialize_conversation(conversation):
    latest_message = (
        ChatMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    job_context = _get_chat_context(conversation, kind="job_description")
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "latest_message": latest_message.content if latest_message else "",
        "has_job_description": job_context is not None,
        "job_description_excerpt": _text_excerpt(
            job_context.content if job_context else "",
            limit=120,
        ),
    }


def _serialize_chat_job_context(conversation, include_content=False):
    job_context = _get_chat_context(conversation, kind="job_description")
    if job_context is None:
        return {
            "has_job_description": False,
            "content": "" if include_content else None,
            "excerpt": "",
            "updated_at": None,
        }

    payload = {
        "has_job_description": True,
        "excerpt": _text_excerpt(job_context.content, limit=180),
        "updated_at": job_context.updated_at.isoformat(),
    }
    if include_content:
        payload["content"] = job_context.content
    return payload


def _get_chat_context(conversation, kind):
    if conversation is None or conversation.id is None:
        return None

    return ChatConversationContext.query.filter_by(
        conversation_id=conversation.id,
        user_id=current_user.id,
        kind=kind,
    ).first()


def _upsert_chat_context(conversation, kind, title, content):
    record = _get_chat_context(conversation, kind)
    if record is None:
        record = ChatConversationContext(
            conversation_id=conversation.id,
            user_id=current_user.id,
            kind=kind,
            title=title,
            content=content,
        )
    else:
        record.title = title
        record.content = content
        record.updated_at = utc_now()

    db.session.add(record)
    return record


def _delete_chat_context(conversation, kind):
    record = _get_chat_context(conversation, kind)
    if record is not None:
        db.session.delete(record)


def _chat_tool_message_or_404(message_id, tool_action):
    message = (
        ChatMessage.query.join(ChatConversation)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.role == "assistant",
            ChatConversation.user_id == current_user.id,
        )
        .first_or_404()
    )
    if _message_metadata(message).get("tool_action") != tool_action:
        abort(404)
    return message


def _send_chat_artifact_pdf(pdf, filename_prefix, role_title=""):
    filename_parts = [filename_prefix]
    if role_title:
        filename_parts.append(secure_filename(role_title.lower()) or "role")
    download_name = "-".join(filename_parts) + ".pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


def _text_excerpt(text, limit=180):
    excerpt = " ".join((text or "").split())
    if len(excerpt) <= limit:
        return excerpt
    return f"{excerpt[: limit - 3].rstrip()}..."


def _serialize_message(message):
    metadata = _message_metadata(message)
    metadata.pop("cover_letter_payload", None)
    if metadata.get("tool_action") == "cover_letter":
        metadata["download_url"] = url_for(
            "main.download_chat_cover_letter",
            message_id=message.id,
        )
    elif metadata.get("tool_action") == "cv_tailoring_plan":
        metadata["download_url"] = url_for(
            "main.download_chat_cv_tailoring_plan",
            message_id=message.id,
        )
    elif metadata.get("tool_action") == "interview_prep":
        metadata["download_url"] = url_for(
            "main.download_chat_interview_prep",
            message_id=message.id,
        )
    elif metadata.get("tool_action") == "skill_gap_plan":
        metadata["download_url"] = url_for(
            "main.download_chat_skill_gap_plan",
            message_id=message.id,
        )
    elif metadata.get("tool_action") == "career_roadmap":
        metadata["download_url"] = url_for(
            "main.download_chat_career_roadmap",
            message_id=message.id,
        )

    feedback = None
    if message.role == "assistant":
        feedback_record = ChatFeedback.query.filter_by(
            message_id=message.id,
            user_id=current_user.id,
        ).first()
        feedback = feedback_record.rating if feedback_record else None

    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "metadata": metadata,
        "feedback": feedback,
        "created_at": message.created_at.isoformat(),
    }


def _message_metadata(message):
    if not message.metadata_json:
        return {}

    try:
        return json.loads(message.metadata_json)
    except json.JSONDecodeError:
        return {}


def _chat_title_from_message(message):
    title = " ".join((message or "").split())
    if len(title) > 64:
        title = f"{title[:61].rstrip()}..."
    return title or "New chat"


def _chat_requests_skill_gap_tracking(message):
    text = " ".join((message or "").lower().split())
    return any(
        phrase in text
        for phrase in (
            "skill gap",
            "skill gaps",
            "missing skill",
            "missing skills",
            "gaps to address",
            "highlight my gaps",
            "highlight the gaps",
            "what am i missing",
        )
    )


def _selected_chat_cv(cv_id):
    if cv_id:
        return CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
    return (
        CV.query.filter_by(user_id=current_user.id)
        .order_by(CV.created_at.desc())
        .first()
    )
