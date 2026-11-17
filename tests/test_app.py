import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from werkzeug.security import check_password_hash

from app import create_app
from app.db import get_db
from app.rules import clockwork, habit_reader, outcome

PASSWORD = "made-up-orbit-42"
NEW_PASSWORD = "another-fake-meteor-73"


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "SECRET_KEY": "isolated-test-key", "DATABASE": str(tmp_path / "test.sqlite")})


@pytest.fixture()
def client(app):
    return app.test_client()


def token(client, path="/login"):
    page = client.get(path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
    assert match, page.data.decode()
    return match.group(1).decode()


def post(client, path, data, csrf_page="/dashboard", follow=True):
    return client.post(path, data={**data, "csrf_token": token(client, csrf_page)}, follow_redirects=follow)


def register(client, username="leah", name="Leah"):
    return post(client, "/register", {"username": username, "display_name": name, "password": PASSWORD}, "/register")


def login(client, username="leah", password=PASSWORD):
    return post(client, "/login", {"username": username, "password": password}, "/login")


def start(client, bot="clockwork"):
    response = post(client, "/rounds", {"bot": bot}, follow=False)
    assert response.status_code == 303
    return int(response.headers["Location"].split("/")[-1])


def play(client, move="paper", bot="clockwork"):
    round_id = start(client, bot)
    return round_id, post(client, f"/rounds/{round_id}/move", {"move": move})


@pytest.mark.parametrize("player,bot,expected", [
    ("rock", "rock", "tie"), ("rock", "paper", "loss"), ("rock", "scissors", "win"),
    ("paper", "rock", "win"), ("paper", "paper", "tie"), ("paper", "scissors", "loss"),
    ("scissors", "rock", "loss"), ("scissors", "paper", "win"), ("scissors", "scissors", "tie"),
])
def test_all_nine_rules(player, bot, expected):
    assert outcome(player, bot) == expected


@pytest.mark.parametrize("player,bot", [("lizard", "rock"), ("rock", "fire"), (None, "rock")])
def test_invalid_rules(player, bot):
    with pytest.raises(ValueError):
        outcome(player, bot)


def test_strategies_use_only_prior_history():
    assert [clockwork(["rock"] * n) for n in range(4)] == ["rock", "paper", "scissors", "rock"]
    assert habit_reader([]) == "rock"
    assert habit_reader(["scissors", "scissors", "rock"]) == "rock"
    assert habit_reader(["rock", "paper"]) == "paper"  # fixed tie ordering


def test_registration_empty_dashboard_and_hash(client, app):
    response = register(client)
    assert b"Your story starts with one move" in response.data
    assert b"0 saved rounds" in response.data
    with app.app_context():
        row = get_db().execute("SELECT * FROM users").fetchone()
        assert row["password_hash"] != PASSWORD
        assert check_password_hash(row["password_hash"], PASSWORD)
        assert get_db().execute("SELECT COUNT(*) FROM login_sessions").fetchone()[0] == 1


def test_duplicate_registration_and_case_normalization(client):
    register(client, "Leah")
    post(client, "/logout", {})
    response = register(client, "LEAH")
    assert b"That username is taken" in response.data
    assert b"Sign out</button>" not in response.data


@pytest.mark.parametrize("data,expected", [
    ({"username": "ab"}, b"3\xe2\x80\x9324"),
    ({"display_name": " "}, b"1\xe2\x80\x9340"),
    ({"password": "short"}, b"12\xe2\x80\x93128"),
])
def test_invalid_registration(client, data, expected):
    fields = {"username": "valid", "display_name": "Valid", "password": PASSWORD}
    fields.update(data)
    response = post(client, "/register", fields, "/register")
    assert expected in response.data
    assert client.get("/api/rounds/1").status_code == 401


def test_wrong_password_and_unknown_user(client):
    register(client)
    post(client, "/logout", {})
    for username, password in [("leah", "wrong"), ("unknown", PASSWORD)]:
        assert b"was not recognized" in login(client, username, password).data
        assert client.get("/dashboard").status_code == 302
    assert b"Welcome back" in login(client).data


def test_authoritative_result_dashboard_replay_and_refresh(client, app):
    register(client)
    round_id = start(client)
    response = post(client, f"/rounds/{round_id}/move", {"move": "paper", "outcome": "loss", "bot_move": "scissors", "user_id": 999})
    assert b"You win. Nice read." in response.data
    data = client.get(f"/api/rounds/{round_id}").json
    assert (data["player_move"], data["bot_move"], data["outcome"]) == ("paper", "rock", "win")
    post(client, f"/rounds/{round_id}/move", {"move": "scissors"})
    assert client.get(f"/api/rounds/{round_id}").json == data
    assert b"1 saved round" in client.get("/dashboard").data
    assert b"You win. Nice read." in client.get(f"/rounds/{round_id}").data
    second, _ = play(client, "scissors")  # second Clockwork move is paper
    assert second != round_id
    assert client.get(f"/api/rounds/{second}").json["outcome"] == "win"
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM rounds WHERE outcome IS NOT NULL").fetchone()[0] == 2


def test_both_strategy_paths_and_saved_tie_loss(client):
    register(client)
    first, _ = play(client, "rock", "habit-reader")
    assert client.get(f"/api/rounds/{first}").json["outcome"] == "tie"
    second, _ = play(client, "rock", "habit-reader")
    assert client.get(f"/api/rounds/{second}").json["outcome"] == "loss"
    page = client.get("/dashboard").data
    assert b"2 saved rounds" in page
    assert b"Habit Reader" in page


def test_invalid_move_or_bot_does_not_save_result(client, app):
    register(client)
    assert post(client, "/rounds", {"bot": "cheater"}).status_code == 400
    round_id = start(client)
    assert post(client, f"/rounds/{round_id}/move", {"move": "lizard"}).status_code == 400
    assert client.get(f"/api/rounds/{round_id}").json["outcome"] is None
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM rounds WHERE outcome IS NOT NULL").fetchone()[0] == 0


def test_second_user_direct_access_is_denied(client, app):
    register(client)
    round_id, _ = play(client)
    other = app.test_client()
    register(other, "omar", "Omar")
    for path in [f"/rounds/{round_id}", f"/api/rounds/{round_id}"]:
        assert other.get(path).status_code == 404
    assert post(other, f"/rounds/{round_id}/move", {"move": "rock"}).status_code == 404
    assert b"No saved rounds yet" in other.get("/dashboard").data
    # An injected user_id cannot redirect account changes to another user.
    post(other, "/account", {"display_name": "Omar revised", "user_id": "1"})
    with app.app_context():
        names = [r[0] for r in get_db().execute("SELECT display_name FROM users ORDER BY id")]
        assert names == ["Leah", "Omar revised"]
    assert b"1 saved round" in client.get("/dashboard").data


def test_display_name_validation_and_html_escaping(client):
    register(client)
    assert b"1\xe2\x80\x9340" in post(client, "/account", {"display_name": " "}).data
    post(client, "/account", {"display_name": "<script>alert(1)</script>"})
    page = client.get("/dashboard").data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert b"<script>alert(1)</script>" not in page


def test_password_checks_then_revokes_all_sessions(client, app):
    register(client)
    other_session = app.test_client()
    login(other_session)
    old_cookie = client.get_cookie("session").value
    bad = post(client, "/account/password", {"current_password": "wrong", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
    assert b"Nothing changed" in bad.data
    mismatch = post(client, "/account/password", {"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": "not-the-same"})
    assert b"do not match" in mismatch.data
    changed = post(client, "/account/password", {"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
    assert b"All sessions were signed out" in changed.data
    assert other_session.get("/dashboard").status_code == 302
    replay = app.test_client()
    replay.set_cookie("session", old_cookie)
    assert replay.get("/api/rounds/1").status_code == 401
    assert b"was not recognized" in login(client).data
    assert b"Welcome back" in login(client, password=NEW_PASSWORD).data


def test_logout_revokes_old_cookie_and_direct_request(client, app):
    register(client)
    round_id, _ = play(client)
    cookie = client.get_cookie("session").value
    assert b"Your scores are saved" in post(client, "/logout", {}).data
    assert client.get(f"/api/rounds/{round_id}").status_code == 401
    replay = app.test_client()
    replay.set_cookie("session", cookie)
    assert replay.get("/dashboard").status_code == 302
    login(client)
    assert b"1 saved round" in client.get("/dashboard").data


def test_csrf_required_for_registration_login_and_every_mutation(client):
    assert client.post("/register", data={"username": "forged"}).status_code == 400
    assert client.post("/login", data={}).status_code == 400
    register(client)
    round_id = start(client)
    for path in ["/rounds", f"/rounds/{round_id}/move", "/account", "/account/password", "/logout"]:
        assert client.post(path, data={}).status_code == 400
    assert client.get("/logout").status_code == 405


def test_data_and_server_sessions_survive_app_restart(client, app):
    register(client)
    round_id, _ = play(client)
    cookie = client.get_cookie("session").value
    restarted = create_app({"TESTING": True, "SECRET_KEY": "isolated-test-key", "DATABASE": app.config["DATABASE"]})
    returning = restarted.test_client()
    returning.set_cookie("session", cookie)
    assert b"1 saved round" in returning.get("/dashboard").data
    assert returning.get(f"/api/rounds/{round_id}").json["outcome"] == "win"


def test_expired_server_session_denied(client, app):
    register(client)
    with app.app_context():
        get_db().execute("UPDATE login_sessions SET expires_at=0")
        get_db().commit()
    assert client.get("/api/rounds/1").status_code == 401


def test_parallel_duplicate_requests_save_only_once(client, app):
    register(client)
    round_id = start(client)
    csrf = token(client, f"/rounds/{round_id}")
    cookie = client.get_cookie("session").value
    def submit(_):
        parallel = app.test_client()
        parallel.set_cookie("session", cookie)
        return parallel.post(f"/rounds/{round_id}/move", data={"csrf_token": csrf, "move": "paper"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(submit, range(2))) == [303, 303]
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM rounds WHERE outcome IS NOT NULL").fetchone()[0] == 1
    assert b"1 saved round" in client.get("/dashboard").data
