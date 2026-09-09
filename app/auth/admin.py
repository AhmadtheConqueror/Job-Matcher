from functools import wraps

from flask import abort, current_app
from flask_login import current_user, login_required


def is_admin_email(email):
    admin_emails = current_app.config.get("ADMIN_EMAILS", set())
    if isinstance(admin_emails, str):
        admin_emails = _parse_admin_emails(admin_emails)
    else:
        try:
            admin_emails = {
                str(value).strip().lower()
                for value in admin_emails
                if str(value).strip()
            }
        except TypeError:
            admin_emails = set()
    return str(email or "").strip().lower() in admin_emails


def has_admin_access(user):
    return bool(user and user.is_authenticated and is_admin_email(user.email))


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not has_admin_access(current_user):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def _parse_admin_emails(raw_value):
    return {
        email.strip().lower()
        for email in str(raw_value or "").split(",")
        if email.strip()
    }
