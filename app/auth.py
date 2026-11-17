"""Flask-Login identifies users; database records allow immediate revocation."""
import re
import secrets
import sqlite3
import time

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db

bp = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.display_name = row["display_name"]


@login_manager.user_loader
def load_user(user_id):
    # A signed cookie alone is insufficient: require a live server-side record.
    row = get_db().execute("""
      SELECT u.* FROM users u JOIN login_sessions s ON s.user_id=u.id
      WHERE u.id=? AND s.id=? AND s.auth_version=u.auth_version AND s.expires_at>?
    """, (user_id, session.get("login_id", ""), int(time.time()))).fetchone()
    return User(row) if row else None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify(error="Sign in to view your results."), 401
    flash("Sign in to continue.", "info")
    return redirect(url_for("auth.login"))


def establish_session(row):
    session.clear()
    login_id = secrets.token_urlsafe(32)
    db = get_db()
    db.execute("DELETE FROM login_sessions WHERE expires_at<=?", (int(time.time()),))
    db.execute("INSERT INTO login_sessions VALUES (?,?,?,?)", (login_id, row["id"], row["auth_version"], int(time.time()) + 8 * 3600))
    db.commit()
    session["login_id"] = login_id
    session.permanent = True
    login_user(User(row), remember=False, fresh=True)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("game.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        error = None
        if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
            error = "Use 3–24 letters, numbers or underscores for your username."
        elif not 1 <= len(display_name) <= 40:
            error = "Use a display name of 1–40 characters."
        elif not 12 <= len(password) <= 128:
            error = "Use a password of 12–128 characters. Use a made-up password for this local demo."
        if not error:
            db = get_db()
            try:
                cursor = db.execute("INSERT INTO users (username,display_name,password_hash) VALUES (?,?,?)", (username, display_name, generate_password_hash(password)))
                db.commit()
                row = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
            except sqlite3.IntegrityError:
                db.rollback()
                error = "That username is taken. Try another one."
            else:
                establish_session(row)
                flash("Account ready. Pick your first opponent.", "success")
                return redirect(url_for("game.dashboard"), 303)
        flash(error, "error")
    return render_template("auth.jinja", registering=True)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("game.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        row = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row and len(password) <= 128 and check_password_hash(row["password_hash"], password):
            establish_session(row)
            flash("Welcome back.", "success")
            return redirect(url_for("game.dashboard"), 303)
        flash("Username or password was not recognized. Try again.", "error")
    return render_template("auth.jinja", registering=False)


@bp.post("/logout")
@login_required
def logout():
    db = get_db()
    db.execute("DELETE FROM login_sessions WHERE id=?", (session.get("login_id"),))
    db.commit()
    logout_user()
    session.clear()
    flash("Signed out. Your scores are saved.", "success")
    return redirect(url_for("game.home"), 303)


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        if not 1 <= len(display_name) <= 40:
            flash("Use a display name of 1–40 characters.", "error")
        else:
            db = get_db()
            db.execute("UPDATE users SET display_name=? WHERE id=?", (display_name, current_user.id))
            db.commit()
            flash("Display name updated.", "success")
            return redirect(url_for("auth.account"), 303)
    return render_template("account.jinja")


@bp.post("/account/password")
@login_required
def password():
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id=?", (current_user.id,)).fetchone()
    previous = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if len(previous) > 128 or not check_password_hash(row["password_hash"], previous):
        flash("Your current password was not recognized. Nothing changed.", "error")
    elif not 12 <= len(new) <= 128:
        flash("Use a new password of 12–128 characters.", "error")
    elif new != confirm:
        flash("The new passwords do not match.", "error")
    elif new == previous:
        flash("Choose a different new password.", "error")
    else:
        db.execute("UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE id=?", (generate_password_hash(new), current_user.id))
        db.execute("DELETE FROM login_sessions WHERE user_id=?", (current_user.id,))
        db.commit()
        logout_user()
        session.clear()
        flash("Password changed. All sessions were signed out. Sign in with your new password.", "success")
        return redirect(url_for("auth.login"), 303)
    return redirect(url_for("auth.account"), 303)
