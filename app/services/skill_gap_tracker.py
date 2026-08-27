from app import db
from app.models import SkillGap, utc_now
from app.services.cv_insights import detect_known_skills


SKILL_GAP_STATUSES = {"open", "learning", "done"}
SKILL_GAP_PRIORITIES = {"high", "medium", "low"}


def track_skill_gaps_from_text(user_id, cv_text, job_text, source="Chat skill gap plan"):
    cv_skills = {skill.lower() for skill in detect_known_skills(cv_text)}
    job_skills = detect_known_skills(job_text)
    missing_skills = [
        skill
        for skill in job_skills
        if skill.lower() not in cv_skills
    ]

    tracked = []
    for index, skill in enumerate(missing_skills):
        record = SkillGap.query.filter_by(user_id=user_id, skill=skill).first()
        if record is None:
            record = SkillGap(
                user_id=user_id,
                skill=skill,
                status="open",
                priority="high" if index < 3 else "medium",
                source=source,
            )
        else:
            record.source = source
            record.updated_at = utc_now()
            if record.status not in SKILL_GAP_STATUSES:
                record.status = "open"
            if record.priority not in SKILL_GAP_PRIORITIES:
                record.priority = "medium"

        db.session.add(record)
        tracked.append(record)

    return tracked


def serialize_skill_gap(record):
    return {
        "id": record.id,
        "skill": record.skill,
        "status": record.status,
        "priority": record.priority,
        "source": record.source,
        "notes": record.notes or "",
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
