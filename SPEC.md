# Sneaky Robot RPS — Project Record

## Project and current status
- **Audience:** casual players who like beating a computer.
- **Main task:** play Rock, Paper, Scissors against a sneaky robot that tries to predict my next move, then see my saved results.
- **Dream:** A robot opponent with a personality that learns my habits, taunts me when it predicts me right, and gets smarter the more I play.
- **Promise:** A casual player can sign up, play RPS against a sneaky robot that tries to predict their next move, see their saved wins/losses/ties on a private dashboard, and update their display name and password.
- **Experiment:** Add a one-time "power card" (for example, see the robot's prediction once per game). If it makes the game confusing or breaks the saved scores, I'll remove it and keep the plain game.
- **Stack:** Python 3.12 + Flask + SQLite + Flask-Login, tested with pytest. Same language and test tools I used for RPS-001, and the course's Bot Lab example uses this stack with working accounts and saved scores, so I can build on a checked foundation and focus on the sneaky robot.
- **Deferred:** public leaderboard, multiplayer, email/password reset, online hosting.
- **Repository:** https://github.com/ac2928/sneaky-robot-rps
- **Current stage:** Review 1 (Plan). No code yet. Checks: none run yet (planning stage).

## 1 · Plan

### Two concepts
| | A: RPS vs a sneaky robot | B: RPS with a power card |
|---|---|---|
| Idea | The robot watches my past moves and tries to predict and beat my next one. | Once per game I can play a special card, like seeing the robot's move. |
| Effort | Lower: the course's Bot Lab example already has a robot that counters a player's most common move, so I can customize it. | Higher: new rules, tracking whether the card was used, and more tests. |
| Fit with dashboard | Simple wins/losses/ties against the robot. | Scoring gets more complicated. |

**Choice:** A, the sneaky robot. **Reason:** I can finish the full account → game → dashboard journey reliably. **Tradeoff:** less new game mechanics, so B becomes my Experiment instead of being dropped.

**Assumptions still to check:** that casual players find the robot's predictions fun rather than frustrating, which a classmate will try.

### Five stories
| # | Story | Check |
|---|---|---|
| 1 | **Join and return:** As a casual player, I can sign up, sign in, and come back later. | A new account works; a duplicate username or wrong password shows a clear error; passwords are stored hashed. |
| 2 | **Play and save:** As a signed-in player, I can play a round against the sneaky robot, and my result is saved to my account. | The server decides the winner using the nine RPS rules and saves one result; repeating the same request doesn't save it twice. |
| 3 | **See my progress:** As a player, I can see my own wins, losses, ties, and recent rounds on a private dashboard. | A new account shows an empty-state message; totals are correct and still there after a refresh or restart. |
| 4 | **Maintain my account:** As a player, I can change my display name and my password by entering my current password. | After a password change, the old password fails and the new one works. |
| 5 | **Leave safely:** As a player, I can sign out, and nobody can see my private data afterward. | After logout, opening the dashboard directly is denied, and another player can't see my results. |

### Architecture sketch
    Player's browser
         |  (sign up, play a move, view dashboard, change name)
         v
    Flask web app
      - Accounts (auth.py): sign up / sign in / sign out, checks who you are
      - Game (game.py): takes my move, asks the robot for its move, decides the result, saves it
      - Robot + rules (rules.py): the nine RPS rules + the sneaky robot that predicts from my past moves
      - Dashboard / account pages: show only my saved results; edit name/password
         |
         v
    SQLite database
      - users (username, hashed password, display name)
      - rounds (which user, my move, robot move, result, time)

The robot picks its move without seeing my current move. **The core rules live in `rules.py`.** Results are saved under my account only, and the dashboard reads only my rows.

### Pattern experiment
- **Problem:** The robot needs a way to choose its move, and I may want more than one robot style later.
- **Two approaches:** (A) a simple if/else inside the game code, or (B) the Strategy pattern, where each robot style is its own small function, like `sneaky_robot(history)`, that the game can swap in.
- **Planned comparison:** Build B and test both robot functions with the same move histories. Keep B only if it makes adding or testing a robot easier than the if/else; otherwise go back to the simpler code.

### AI experiment
- **Prediction:** I expect the AI to write the sneaky robot quickly, but it might accidentally let the robot see my current move, which would be cheating.
- **How I'll check:** I'll write my own test first, with expected results decided by me, proving the robot only uses my past moves, and run it against the AI's code.

### Help received
Claude (chat assistant) explained the assignment and helped me organize my decisions; I chose the concepts, audience, and plan.