import json
import re
from collections import Counter, defaultdict

from app.models import ChatConversation, ChatFeedback, ChatMessage, SkillGap
from app.services.prompt_versions import ACTIVE_PROMPT_VERSIONS


LEGACY_PROMPT_VERSION = "legacy-unversioned"


def build_evaluation_dashboard(user):
    conversations_count = ChatConversation.query.filter_by(user_id=user.id).count()
    messages = (
        ChatMessage.query.join(ChatConversation)
        .filter(ChatConversation.user_id == user.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    feedback_records = (
        ChatFeedback.query.join(ChatMessage)
        .join(ChatConversation)
        .filter(ChatConversation.user_id == user.id)
        .order_by(ChatFeedback.created_at.desc())
        .all()
    )
    skill_gaps = SkillGap.query.filter_by(user_id=user.id).all()

    assistant_messages = [message for message in messages if message.role == "assistant"]
    user_messages = [message for message in messages if message.role == "user"]
    tool_counts = Counter()
    prompt_counts = Counter()

    for message in assistant_messages:
        metadata = load_message_metadata(message)
        tool_counts[metadata.get("tool_action") or "chat_reply"] += 1
        prompt_counts[metadata.get("prompt_version") or LEGACY_PROMPT_VERSION] += 1

    rating_counts = Counter(record.rating for record in feedback_records)
    skill_gap_counts = Counter(record.status for record in skill_gaps)
    dataset_examples = build_anonymized_training_examples(user, messages=messages)

    return {
        "totals": {
            "conversations": conversations_count,
            "messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "feedback": len(feedback_records),
            "dataset_examples": len(dataset_examples),
        },
        "tool_counts": _counter_rows(tool_counts),
        "prompt_counts": _counter_rows(prompt_counts),
        "rating_counts": _counter_rows(rating_counts),
        "skill_gap_counts": _counter_rows(skill_gap_counts),
        "active_prompt_versions": ACTIVE_PROMPT_VERSIONS,
        "recent_feedback": [
            {
                "rating": record.rating,
                "note": record.note or "",
                "message_excerpt": _excerpt(record.message.content, 220),
                "created_at": record.created_at,
            }
            for record in feedback_records[:8]
        ],
    }


def build_anonymized_training_jsonl(user):
    examples = build_anonymized_training_examples(user)
    return "\n".join(json.dumps(example, ensure_ascii=False) for example in examples)


def build_anonymized_training_examples(user, messages=None):
    if messages is None:
        messages = (
            ChatMessage.query.join(ChatConversation)
            .filter(ChatConversation.user_id == user.id)
            .order_by(ChatMessage.conversation_id.asc(), ChatMessage.created_at.asc())
            .all()
        )

    feedback_by_message_id = {
        feedback.message_id: feedback.rating
        for feedback in ChatFeedback.query.filter_by(user_id=user.id).all()
    }
    grouped_messages = defaultdict(list)
    for message in messages:
        grouped_messages[message.conversation_id].append(message)

    examples = []
    for conversation_messages in grouped_messages.values():
        last_user_message = None
        for message in conversation_messages:
            if message.role == "user":
                last_user_message = message
                continue
            if message.role != "assistant" or last_user_message is None:
                continue

            metadata = load_message_metadata(message)
            examples.append(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": anonymize_text(last_user_message.content, user),
                        },
                        {
                            "role": "assistant",
                            "content": anonymize_text(message.content, user),
                        },
                    ],
                    "metadata": {
                        "prompt_version": metadata.get("prompt_version")
                        or LEGACY_PROMPT_VERSION,
                        "tool_action": metadata.get("tool_action") or "chat_reply",
                        "feedback_rating": feedback_by_message_id.get(message.id),
                        "used_latest_cv": bool(metadata.get("used_latest_cv")),
                        "used_job_description": bool(
                            metadata.get("used_job_description")
                        ),
                    },
                }
            )

    return examples


def load_message_metadata(message):
    if not message.metadata_json:
        return {}
    try:
        return json.loads(message.metadata_json)
    except json.JSONDecodeError:
        return {}


def anonymize_text(text, user):
    anonymized = text or ""
    anonymized = re.sub(r"https?://\S+|www\.\S+", "[URL]", anonymized)
    anonymized = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[EMAIL]",
        anonymized,
        flags=re.IGNORECASE,
    )
    anonymized = re.sub(
        r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)",
        "[PHONE]",
        anonymized,
    )

    name_parts = [part for part in (user.name or "").split() if len(part) > 1]
    for part in sorted(name_parts, key=len, reverse=True):
        anonymized = re.sub(
            rf"\b{re.escape(part)}\b",
            "[NAME]",
            anonymized,
            flags=re.IGNORECASE,
        )

    return anonymized


def _counter_rows(counter):
    return [
        {"label": label, "count": count}
        for label, count in counter.most_common()
    ]


def _excerpt(text, limit):
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."
