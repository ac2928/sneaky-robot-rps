"""The rules do not depend on Flask, a database, or the interface."""
from collections import Counter

MOVES = ("rock", "paper", "scissors")
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


def outcome(player, opponent):
    if player not in MOVES or opponent not in MOVES:
        raise ValueError("Choose rock, paper or scissors.")
    if player == opponent:
        return "tie"
    return "win" if BEATS[player] == opponent else "loss"


def clockwork(history):
    """Predictable cycle; only completed, earlier rounds are supplied."""
    return MOVES[len(history) % 3]


def habit_reader(history):
    """Counter the most frequent earlier move. Ties use MOVES order."""
    if not history:
        return "rock"
    counts = Counter(history)
    frequent = max(MOVES, key=lambda move: counts[move])
    return next(move for move in MOVES if BEATS[move] == frequent)


STRATEGIES = {"clockwork": clockwork, "habit-reader": habit_reader}
BOT_NAMES = {"clockwork": "Clockwork", "habit-reader": "Habit Reader"}
