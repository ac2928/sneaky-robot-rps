from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from .db import get_db
from .rules import BOT_NAMES, MOVES, STRATEGIES, outcome

bp = Blueprint("game", __name__)


def owned_round(round_id):
    row = get_db().execute("SELECT * FROM rounds WHERE id=? AND user_id=?", (round_id, current_user.id)).fetchone()
    if not row:
        abort(404)
    return row


@bp.get("/")
def home():
    return render_template("home.jinja")


@bp.get("/dashboard")
@login_required
def dashboard():
    rows = get_db().execute("SELECT * FROM rounds WHERE user_id=? AND outcome IS NOT NULL ORDER BY id DESC", (current_user.id,)).fetchall()
    totals = {name: sum(row["outcome"] == name for row in rows) for name in ("win", "loss", "tie")}
    return render_template("dashboard.jinja", rounds=rows[:20], total=len(rows), totals=totals, bot_names=BOT_NAMES)


@bp.post("/rounds")
@login_required
def new_round():
    bot = request.form.get("bot", "")
    if bot not in STRATEGIES:
        abort(400, "Choose a listed opponent.")
    db = get_db()
    cursor = db.execute("INSERT INTO rounds (user_id,bot) VALUES (?,?)", (current_user.id, bot))
    db.commit()
    return redirect(url_for("game.arena", round_id=cursor.lastrowid), 303)


@bp.get("/rounds/<int:round_id>")
@login_required
def arena(round_id):
    row = owned_round(round_id)
    return render_template("arena.jinja", game=row, bot_name=BOT_NAMES[row["bot"]])


@bp.post("/rounds/<int:round_id>/move")
@login_required
def move(round_id):
    player = request.form.get("move", "")
    if player not in MOVES:
        abort(400, "Choose rock, paper or scissors.")
    db = get_db()
    # Serialize reads/writes: two simultaneous retries cannot score a round twice.
    db.execute("BEGIN IMMEDIATE")
    row = owned_round(round_id)
    if row["outcome"] is None:
        history = [r["player_move"] for r in db.execute("SELECT player_move FROM rounds WHERE user_id=? AND outcome IS NOT NULL ORDER BY id", (current_user.id,)).fetchall()]
        opponent = STRATEGIES[row["bot"]](history)
        result = outcome(player, opponent)
        db.execute("UPDATE rounds SET player_move=?,bot_move=?,outcome=? WHERE id=? AND user_id=? AND outcome IS NULL", (player, opponent, result, round_id, current_user.id))
    db.commit()
    return redirect(url_for("game.arena", round_id=round_id), 303)


@bp.get("/api/rounds/<int:round_id>")
@login_required
def round_data(round_id):
    row = owned_round(round_id)
    return jsonify({key: row[key] for key in ("id", "bot", "player_move", "bot_move", "outcome", "created_at")})
