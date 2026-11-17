"""Factory: framework owns cookies, password helpers, login and CSRF handling."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect, CSRFError


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True, instance_path=os.environ.get("ARENA_INSTANCE"))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("ARENA_SECRET_KEY"),
        DATABASE=str(Path(app.instance_path) / "arena.sqlite"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("ARENA_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        key_path = Path(app.instance_path) / "secret-key"
        if not key_path.exists():
            try:
                descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "w") as stream:
                    stream.write(secrets.token_hex(32))
        app.config["SECRET_KEY"] = key_path.read_text().strip()
    app.jinja_env.autoescape = True
    CSRFProtect(app)
    from .db import close_db, init_db
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
    from . import auth, game
    auth.login_manager.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(game.bp)

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_template("error.jinja", title="Please refresh and try again", message="This form has expired or its security token is missing. Return to the page, refresh it, then try once more."), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.jinja", title="Round or page not found", message="That item is unavailable. Your own saved rounds are on your dashboard."), 404

    @app.after_request
    def private_cache(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response
    return app
