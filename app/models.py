from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    cvs = db.relationship("CV", backref="user", lazy=True, cascade="all, delete-orphan")
    jobs = db.relationship(
        "JobDescription", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    analyses = db.relationship(
        "AnalysisResult", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    chat_conversations = db.relationship(
        "ChatConversation", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    skill_gaps = db.relationship(
        "SkillGap", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class CV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    analyses = db.relationship(
        "AnalysisResult", backref="cv", lazy=True, cascade="all, delete-orphan"
    )


class JobDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    company = db.Column(db.String(180))
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    analyses = db.relationship(
        "AnalysisResult",
        backref="job_description",
        lazy=True,
        cascade="all, delete-orphan",
    )


class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    cv_id = db.Column(db.Integer, db.ForeignKey("cv.id"), nullable=False)
    job_description_id = db.Column(
        db.Integer, db.ForeignKey("job_description.id"), nullable=False
    )
    result_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)


class SkillGap(db.Model):
    __table_args__ = (
        db.UniqueConstraint("user_id", "skill", name="uq_skill_gap_user_skill"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    skill = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="open")
    priority = db.Column(db.String(20), nullable=False, default="medium")
    source = db.Column(db.String(180), nullable=False, default="Chat")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ChatConversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False, default="New chat")
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    messages = db.relationship(
        "ChatMessage",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    contexts = db.relationship(
        "ChatConversationContext",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ChatConversationContext.updated_at.desc()",
    )


class ChatConversationContext(db.Model):
    __table_args__ = (
        db.UniqueConstraint(
            "conversation_id",
            "kind",
            name="uq_chat_conversation_context_kind",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("chat_conversation.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("chat_conversation.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    feedback = db.relationship(
        "ChatFeedback", backref="message", lazy=True, cascade="all, delete-orphan"
    )


class ChatFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_message.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
