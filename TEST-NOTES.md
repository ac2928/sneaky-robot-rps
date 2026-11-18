# Actual verification receipt

**November 3, 2026 (Eastern).** Coding-agent-assisted reference; synthetic users only.

```text
Working directory: docs/public/examples/full-game
Runtime: Python 3.14.7
Command: python -B -m pytest -q -p no:cacheprovider
Result: 30 passed
```

The first collection from the repository root failed because `app` was not on the import path. The corrected package includes `pytest.ini` and documents its working directory; the passing run is a later real execution.

Covered:

- Nine literal RPS answers and invalid rule input.
- Both Strategy functions, earlier history and fixed tie behavior.
- New account, empty dashboard, hashed password, duplicate/case-normalized username and validation errors.
- Wrong password/unknown user, then successful login.
- Backend-authoritative result; supplied outcome/owner fields do not control saving.
- Persisted win/loss/tie history, replay, refresh and duplicate requests.
- Two concurrent requests for one round save one completed result.
- Second-user HTML/JSON/move requests denied; injected owner ID cannot edit someone else.
- Valid/invalid display name and escaped HTML output.
- Wrong current password, mismatched new passwords, change, old-password rejection and all-session revocation.
- Logout invalidates server record; replay of old signed cookie cannot read private data.
- CSRF enabled on registration, login, rounds, moves, name/password edit and logout.
- Data/session persistence across a new app instance with the same database/key.
- Expired server-side session denied.

## Actual browser walkthrough

The coordinating agent used CUA in a browser on the local server on November 3, 2026: registered a fresh synthetic `orbit_leah` account; observed the empty dashboard at zero; chose Clockwork and paper; observed the server return rock and a win; returned to a dashboard with one saved round and one win; changed the display name to Leah Orbit and observed the saved name. A screenshot was recorded in the learner-review outputs.

Password/session maintenance, logout-cookie replay, second-user requests and concurrent duplicate saving are established by the executed automated tests, not claimed as additional browser tasks. This technical browser walkthrough is not a real peer, accessibility audit, public backend, live CI or student understanding. Tests use temporary SQLite databases. Pages serves documentation/download only.

Follow README.md to reproduce. Use `python -B` and disable pytest's cache in the course source tree so generated artifacts are not published as static assets.
