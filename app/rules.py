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


def counter_move(move):
    """The move that beats the given move."""
    return next(choice for choice in MOVES if BEATS[choice] == move)


def clockwork(history):
    """Predictable cycle; only completed, earlier rounds are supplied."""
    return MOVES[len(history) % 3]


def habit_reader(history):
    """Counter the most frequent earlier move. Ties use MOVES order."""
    if not history:
        return "rock"
    counts = Counter(history)
    frequent = max(MOVES, key=lambda move: counts[move])
    return counter_move(frequent)


def sneaky_robot(history):
    """My robot: guess what I usually play right after my last move, then beat it.

    Only earlier, completed rounds are supplied, never the current move.
    No history or no pattern yet: play rock. Ties use MOVES order.
    """
    if not history:
        return "rock"
    last = history[-1]
    followers = Counter(nxt for prev, nxt in zip(history, history[1:]) if prev == last)
    if not followers:
        return "rock"
    guess = max(MOVES, key=lambda move: followers[move])
    return counter_move(guess)


STRATEGIES = {
    "clockwork": clockwork,
    "habit-reader": habit_reader,
    "sneaky-robot": sneaky_robot,
}
BOT_NAMES = {
    "clockwork": "Clockwork",
    "habit-reader": "Habit Reader",
    "sneaky-robot": "Sneaky Robot",
}
