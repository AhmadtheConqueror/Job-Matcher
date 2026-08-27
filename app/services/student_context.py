from app.models import AnalysisResult, CV
from app.services.cv_insights import summarize_analysis_text, summarize_cv_text


MAX_ANALYSES = 3


def build_student_context(user, include_latest_cv=True, cv_id=None):
    lines = [f"Name: {user.name}"]
    used_latest_cv = False
    latest_cv = None
    cv_summary = {}

    if include_latest_cv:
        if cv_id:
            latest_cv = CV.query.filter_by(id=cv_id, user_id=user.id).first()
        if latest_cv is None:
            latest_cv = (
                CV.query.filter_by(user_id=user.id)
                .order_by(CV.created_at.desc())
                .first()
            )

    if latest_cv:
        used_latest_cv = True
        cv_summary = summarize_cv_text(latest_cv.text)
        lines.append(f"Selected CV: {latest_cv.original_filename}")
        _append_cv_summary(lines, cv_summary)
    elif include_latest_cv:
        lines.append("Selected CV: No uploaded CV found.")
    else:
        lines.append("Selected CV: Not included for this message.")

    recent_analyses = (
        AnalysisResult.query.filter_by(user_id=user.id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(MAX_ANALYSES)
        .all()
    )
    if recent_analyses:
        lines.append("Recent saved analyses:")
        for analysis in recent_analyses:
            job = analysis.job_description
            company = f" at {job.company}" if job.company else ""
            excerpt = summarize_analysis_text(analysis.result_text)
            lines.append(f"- {job.title}{company}: {excerpt}")

    return {
        "text": "\n".join(lines),
        "used_latest_cv": used_latest_cv,
        "latest_cv_filename": latest_cv.original_filename if latest_cv else "",
        "selected_cv_id": latest_cv.id if latest_cv else None,
        "detected_skills": cv_summary.get("detected_skills", []),
        "recent_analyses_count": len(recent_analyses),
    }


def context_status_for_user(user):
    latest_cv = (
        CV.query.filter_by(user_id=user.id)
        .order_by(CV.created_at.desc())
        .first()
    )
    recent_analyses_count = AnalysisResult.query.filter_by(user_id=user.id).count()

    cvs = CV.query.filter_by(user_id=user.id).order_by(CV.created_at.desc()).all()
    if not latest_cv:
        return {
            "has_latest_cv": False,
            "latest_cv_filename": "",
            "detected_skills": [],
            "recent_analyses_count": recent_analyses_count,
            "cvs": [],
        }

    summary = summarize_cv_text(latest_cv.text)
    return {
        "has_latest_cv": True,
        "latest_cv_filename": latest_cv.original_filename,
        "detected_skills": summary["detected_skills"],
        "recent_analyses_count": recent_analyses_count,
        "cvs": [
            {
                "id": cv.id,
                "filename": cv.original_filename,
                "created_at": cv.created_at.isoformat(),
            }
            for cv in cvs
        ],
    }


def _append_cv_summary(lines, summary):
    detected_skills = summary.get("detected_skills") or []
    if detected_skills:
        lines.append(f"Detected skills: {', '.join(detected_skills[:18])}")

    for label, key in (
        ("Skills section", "skills_section"),
        ("Education", "education"),
        ("Experience", "experience"),
        ("Projects", "projects"),
        ("Certifications", "certifications"),
        ("General CV evidence", "profile_excerpt"),
    ):
        value = summary.get(key)
        if value:
            lines.append(f"{label}: {value}")
