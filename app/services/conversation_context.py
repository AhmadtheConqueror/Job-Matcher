from dataclasses import dataclass, field

from app.models import ChatConversation, ChatConversationContext, ChatMessage, CV
from app.services.cv_insights import summarize_cv_text
MAX_HISTORY_MESSAGES = 8
MAX_CV_CONTEXT_CHARS = 24000
MAX_DOCUMENT_CONTEXT_CHARS = 24000


@dataclass
class ContextDocument:
    title: str
    content: str
    document_type: str = "document"
    metadata: dict = field(default_factory=dict)


@dataclass
class ConversationContext:
    current_user: object
    active_cv: dict | None
    attached_documents: list[ContextDocument]
    active_job_description: str
    conversation_history: list[ChatMessage]
    current_message: str
    held_instruction: str = ""

    @property
    def has_cv(self):
        return self.active_cv is not None


def build_conversation_context(
    user,
    conversation,
    current_message,
    include_latest_cv=True,
    cv_id=None,
    job_description=None,
    history=None,
):
    active_cv = _active_cv(user, include_latest_cv=include_latest_cv, cv_id=cv_id)
    conversation_contexts = _conversation_contexts(conversation)
    active_job_description = (job_description or "").strip()

    if not active_job_description:
        for context in conversation_contexts:
            if context.document_type == "job_description":
                active_job_description = context.content
                break

    documents = [context for context in conversation_contexts]
    if active_job_description and not any(
        document.document_type == "job_description"
        and document.content == active_job_description
        for document in documents
    ):
        documents.insert(
            0,
            ContextDocument(
                title="Active job description",
                content=active_job_description,
                document_type="job_description",
            ),
        )

    history_messages = (
        list(history)
        if history is not None
        else _recent_messages(conversation)
    )
    return ConversationContext(
        current_user=user,
        active_cv=active_cv,
        attached_documents=documents,
        active_job_description=active_job_description,
        conversation_history=history_messages,
        current_message=(current_message or "").strip(),
        held_instruction=_held_instruction(history_messages, current_message),
    )


def _active_cv(user, include_latest_cv=True, cv_id=None):
    if not include_latest_cv:
        return None

    selected_cv = None
    if cv_id:
        selected_cv = CV.query.filter_by(id=cv_id, user_id=user.id).first()
    if selected_cv is None:
        selected_cv = (
            CV.query.filter_by(user_id=user.id)
            .order_by(CV.created_at.desc())
            .first()
        )
    if selected_cv is None:
        return None

    summary = summarize_cv_text(selected_cv.text or "")
    return {
        "id": selected_cv.id,
        "filename": selected_cv.original_filename,
        "text": (selected_cv.text or "")[:MAX_CV_CONTEXT_CHARS],
        "truncated": len(selected_cv.text or "") > MAX_CV_CONTEXT_CHARS,
        "created_at": selected_cv.created_at.isoformat(),
        "detected_skills": summary.get("detected_skills", []),
    }


def _conversation_contexts(conversation):
    if conversation is None or conversation.id is None:
        return []

    records = (
        ChatConversationContext.query.filter_by(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
        )
        .order_by(ChatConversationContext.updated_at.desc())
        .all()
    )
    return [
        ContextDocument(
            title=record.title,
            content=(record.content or "")[:MAX_DOCUMENT_CONTEXT_CHARS],
            document_type=record.kind,
            metadata={
                "updated_at": record.updated_at.isoformat(),
                "truncated": len(record.content or "") > MAX_DOCUMENT_CONTEXT_CHARS,
            },
        )
        for record in records
        if record.content
    ]


def _recent_messages(conversation):
    if conversation is None or conversation.id is None:
        return []
    messages = (
        ChatMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    return list(reversed(messages))


def _held_instruction(history, current_message=""):
    hold_phrases = (
        "don't evaluate yet",
        "do not evaluate yet",
        "wait until i send my cv",
        "wait until i send the cv",
        "hold off for now",
    )
    continue_phrases = (
        "go ahead",
        "continue",
        "evaluate now",
        "you can evaluate",
        "proceed",
    )
    held = ""
    for message in [*history, _MessageLike(current_message)]:
        if not message.content:
            continue
        normalized = " ".join(message.content.lower().split())
        if any(phrase in normalized for phrase in hold_phrases):
            held = message.content.strip()
        elif any(phrase in normalized for phrase in continue_phrases):
            held = ""
    return held


class _MessageLike:
    role = "user"

    def __init__(self, content):
        self.content = content or ""
