from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
            return render_template("auth/register.html")

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome. Your account is ready.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        login_user(user, remember=bool(request.form.get("remember")))
        flash("Signed in successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))

