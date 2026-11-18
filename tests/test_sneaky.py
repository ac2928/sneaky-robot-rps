"""My tests for the Sneaky Robot. I decided these expected results myself."""

import re

import pytest

from app import create_app
from app.rules import STRATEGIES, sneaky_robot

PASSWORD = "made-up-sneaky-42"


@pytest.mark.parametrize(
    "history,expected",
    [
        ([], "rock"),  # no history: plays rock
        (["rock"], "rock"),  # no pattern yet: plays rock
        (
            ["rock", "paper", "rock"],
            "scissors",
        ),  # after rock I played paper, so it beats paper
        (
            ["paper", "scissors", "paper"],
            "rock",
        ),  # after paper I played scissors, so it beats scissors
        (
            ["scissors", "rock", "scissors"],
            "paper",
        ),  # after scissors I played rock, so it beats rock
    ],
)
def test_sneaky_robot_predicts_from_past_moves(history, expected):
    assert sneaky_robot(history) == expected


def test_sneaky_robot_is_an_opponent():
    assert "sneaky-robot" in STRATEGIES


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "DATABASE": str(tmp_path / "t.sqlite"),
        }
    )
    return app.test_client()


def token(client, path):
    page = client.get(path)
    return re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()


def post(client, path, data, csrf_page="/dashboard", follow=True):
    return client.post(
        path,
        data={**data, "csrf_token": token(client, csrf_page)},
        follow_redirects=follow,
    )


def play(client, move):
    response = post(client, "/rounds", {"bot": "sneaky-robot"}, follow=False)
    round_id = int(response.headers["Location"].split("/")[-1])
    post(client, f"/rounds/{round_id}/move", {"move": move})
    return client.get(f"/api/rounds/{round_id}").get_json()


def test_sneaky_robot_never_sees_my_current_move(client):
    post(
        client,
        "/register",
        {"username": "sneaky_tester", "display_name": "Tester", "password": PASSWORD},
        "/register",
    )
    first = play(client, "rock")
    assert first["bot_move"] == "rock" and first["outcome"] == "tie"
    # Past moves are only ["rock"], so the robot plays rock.
    # If it cheated by seeing "paper", it would play scissors instead.
    second = play(client, "paper")
    assert second["bot_move"] == "rock"
    assert second["outcome"] == "win"
