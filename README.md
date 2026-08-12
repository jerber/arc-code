# arc-code

[Claude Opus 5 scores 30.2%](https://arcprize.org/results/anthropic-claude-opus-5)
on the 25 public ARC-AGI-3 games in ARC's model-only evaluation. I ran the
same model through stock Claude Code, with a shell, a filesystem, and one
command for taking actions. It won 24 of 25 games and scored **96.2%** at the
same `high` reasoning effort, for about **$540**. A second attempt at the one
missed game brings pass@2 to **99.3**, with all 25 games won.

The harness has no solver, planner, world model, or grid tooling. The model
writes those while it plays. In one pass it produced 269 programs—about
12,700 lines, or ten times the size of the harness—and discarded all of them
when their games ended.

This repo contains the harness and six complete session records. The full
post-broker record will be released shortly. The score by itself is not the
interesting part: several systems built specifically for ARC score this high
or higher. What is unusual is where the ARC-specific machinery comes from. It
is not built into the harness. Opus builds it during each game—a parser, a
model of the rules, a simulator, and a search procedure—and throws it away
afterward.

[ARC-AGI-3 is designed](https://arcprize.org/arc-agi/3/) to measure learning
on first contact: an agent has to explore a new environment, infer its goal
and mechanics, build a world model, and revise it from experience. That is
what Opus is doing here through a general coding harness. It builds the
task-specific harness it needs to learn each game. This test-time
meta-learning, rather than the raw score, is the result this repo is meant to
show: the capability is now strong enough to carry nearly the whole benchmark.

Every game runs in its own sandbox with no access to the public internet.
That is enforced rather than left to the model; some of the Codex runs did in
fact try to find published solutions. See [sandboxing](#sandboxing) and
[an agent tried to break out](#an-agent-tried-to-break-out).

## The harness

The agent is stock Claude Code, running headless with six tools pre-approved:
Bash, Read, Write, Edit, Grep, and Glob. There are no MCP servers, subagents,
custom tools, plugins, or hooks. Nothing is fine-tuned, and the agent never
sees an example of a solved game.

The harness itself is three files:

- [`PROMPT.md`](PROMPT.md) gives the method: parse the log with code, keep
  findings in files, test a guess with 1–2 actions before committing 10–20.
  It does not name ARC or contain facts about any game. An eleven-line brief,
  [`ARC.md`](ARC.md), describes the generic interface; the actuator documents
  the board and log format in the log itself. The same prompt is used for
  Claude and Codex. Its portability across tasks is a design claim, [not yet
  a demonstrated result](docs/REPRODUCE.md#what-is-uncertain-stated-plainly).
- [`act.py`](act.py) is the only way the agent touches the game.
  `./act do ACTION1 ACTION6:30,40 --plan "..."` plays actions in order, stops
  when one scores, and appends every action and resulting board to `logs.txt`.
- [`run.py`](run.py) launches one agent session per game and records its full
  event stream. Codex swaps in with one flag; the rest of the harness is the
  same.

`logs.txt`, rather than the context window, is the agent's complete memory.
The model reads it back with grep and Python and keeps longer-lived findings
in files of its own.

Everything supporting those three files lives in [`rig/`](rig): sandboxes,
the broker that holds the game key, the database record, auditing, scoring,
and export. [`rig/README.md`](rig) lists the pieces.

## Results

| | Claude Code (Opus 5) | Codex (gpt-5.6-sol) |
|---|---|---|
| thinking effort | `high` (the default) | `xhigh` |
| ARC score | **96.2%** | 73.7% |
| games won | **24 / 25** | 19 / 25 |
| total actions | **8,789** | 26,971 |
| cost | ~$540 | **~$424** |
| internet access | none | none |

ARC scores action efficiency against human baselines, capped at 100 per game.
Claude's billed cost includes two sessions that crashed or stopped early and
were resumed. Codex reports tokens rather than cost, so its number is computed
from published prices and is a floor. Each column is one pass over the same 25
games with the same prompt and actuator.

These are preliminary runs, intended to test Opus 5's meta-learning through a
general coding harness rather than maximize the score. Claude ran at its
default `high`, and Codex at `xhigh`; higher-effort runs are still to do.

The Claude pass lost one game, `lf52`. Retrying that game once gives
**pass@2 of 99.3** and 25/25 games won. The first failure is discussed below:
[when uncertainty does not lead to action](#when-uncertainty-does-not-lead-to-action).

## Running it

You need Python 3.13+, [uv](https://docs.astral.sh/uv/), an
[E2B](https://e2b.dev) account, a [Neon](https://neon.tech) database, and a
model key. Copy `.env.example` to `.env` and fill it in.

```bash
uv sync
uv run pytest -q                                   # 117 tests, no network
uv run rig/db.py init                              # create the tables
uv run --with e2b rig/cloud.py build               # bake the sandbox image

uv run --with e2b rig/cloud.py start ft09-0d8bbf25 --broker --run smoke
uv run --with e2b rig/cloud.py watch smoke         # progress from the database
```

Add `--agent codex` to run Codex, or pass `$(cat docs/games.txt)` to run all
25 games. [`docs/REPRODUCE.md`](docs/REPRODUCE.md) covers setup, verification,
and the parts of the result that cannot be established from the stored record
alone.

## The agent builds the machinery

Opus starts each game with an empty folder. It usually begins by inspecting a
few boards and writing a parser. As it learns the rules it adds notes, a
simulator, and often a search program. The prompt permits shell and Python
loops but does not ask for any of these things. Across the pass, all 25 games
ended up with their own collection of programs.

Those collections differed substantially. Every game got a parser and 23 of
25 got a search, but only nine got a simulator. `sc25` needed one 79-line
file; `lf52` needed 80 files and 2,288 lines—29 times as much code. A fixed
harness supplies the same machinery to every game in advance. Here the model
decides what to build after it has seen the board.

### One game, start to finish

In `re86`, the player steers shapes around a board to cover colored boxes. The
agent was not told that; [the session](data/runs/re86_v2rest20) had to infer it.

Its first file, `parse.py`, turns each 64×64 board into a list of objects. From
the first few actions it records that arrows move the active shape three cells
at a time, `ACTION5` changes which shape is active, and a purple bar at the
bottom appears to count down the remaining moves. It also records a tentative
goal: four boxes of one color form a plus, and the cross belongs at their
center.

Once those rules seem stable, the agent writes `sim.py` to predict the result
of an action without spending one in the real game. Later levels add a
rectangular ring. The first version, `rect.py`, assumes the ring slides like
the other shapes. The board disproves that: against an obstacle the ring
squashes, holding one edge fixed and expanding sideways. `rect2.py` replaces
the sliding rule; `rect3.py` corrects the order in which the edges grow.

When the simulator matches the observed boards, `route.py` and `game.py`
search it for short winning sequences, which the agent then plays for real.
Eight groups of model files went through at least three versions during the
pass.

### Different games, different machinery

- **`tu93`** ([session](data/runs/tu93_v2sub)) is a maze encoded as a 21×21
  grid of blocks on the 64×64 screen. The agent also infers that the magenta
  bar along the bottom tracks a 50-move budget. A later level adds a pursuer,
  so it writes `chase.py` to search for paths that remain safe against its
  movement.
- **`m0r0`** ([session](data/runs/m0r0_v2rest20)) has two characters that move
  as mirror images. Four solver versions lead to a search state containing
  both positions, the target dot, and the current mode.
- **`lf52`** ([session](data/runs/lf52_v2rest20)) scrolls through a world wider
  than the screen. Six files measure the camera shift, stitch views into a
  map, locate walls, track the camera, and correct clicks for scrolling.
- **`ka59`** becomes a Sokoban search: steer a box around the board and push
  objects into pens. The agent derives the mechanics without being given the
  name.

The agents' `notes.md` files distinguish observations from guesses with labels
such as "hypothesis, strong," "confirmed so far," "presumed," and "untested."
Six complete workspaces are checked into [`data/runs/`](data/runs), including
the notes, programs, action log, and full event stream. The full post-broker
record will be released shortly on the
[releases page](https://github.com/jerber/arc-code/releases).

## Other harnesses

Tycho (100), Retrodict (99.9), and baseline1 (99) report higher scores on
ARC's [community leaderboard](https://arcprize.org/leaderboard/community),
which is separate from the official model-only evaluation. Those systems
include ARC-specific machinery such as grid tools, planners, world-model
contracts, and replay verification. They are stronger results; I am not
claiming a rank over them.

Two general-purpose harnesses make useful comparisons:

- **[PRO-LONG](https://github.com/alexisfox7/PRO-LONG)**
  ([paper](https://arxiv.org/abs/2607.20064)) also runs Claude Code and is the
  source of the log-as-memory idea used here. It reports **97.4% best@2 with
  Fable 5**. Its agent writes a batch of actions and exits; a runner plays the
  batch, so the interaction loop remains in the harness.
- **[Prime Agent](https://www.primeintellect.ai/blog/prime-agent)** is built
  on [`pi`](https://github.com/earendil-works/pi), with recursive context,
  subagents as function calls, and harness state the agent may rewrite during
  a task. It reports **95.5% RHAE Best@1 with Opus 5**.

The cleanest comparison is within Opus 5: 30.2% model-only, 96.2 here, and
95.5 through Prime Agent. ARC-specific machinery still buys the last few
points. Most of the gap, though, appears when the model is allowed to build
its own machinery during the run.

<a id="when-the-model-is-certain-and-wrong"></a>

## When uncertainty does not lead to action

The clearest recurring failure was a gap between uncertainty and action. Opus
would record an unresolved question or an incomplete part of its model, then
keep searching within the model—or stop—instead of using its remaining actions
to investigate the gap.

`lf52` is a peg-solitaire game with ten levels. Level 6 adds a red piece and a
world wider than the screen. Two agents mapped it, built simulators, searched
them, and concluded that the level was impossible. Both stopped with more than
1,700 of their 2,500 actions unused.

One had marked *the red piece cannot board a shuttle* as verified after testing
one way of moving it aboard. A winning run tried a different transition. The
red is a mobile wall: a red-green pair can leapfrog across the board without
consuming the green, and a shuttle can carry the red to where it is needed.
Level 6 then takes about 130 actions, and the game can be completed 10/10.
Across four attempts, two solved it.

Across 191 Claude sessions, 14 did not win. Six were voluntary early exits:
the agent concluded that the current level was impossible and stopped with
1,391–2,218 actions unused. Three of the six had spent less on the level that
beat them than winning sessions spent on average. One declared level 8 of
`bp35` to need an undiscovered mechanic after 52 actions—inside the 20–64 it
had spent on each level it solved—and stopped with 2,162 left.

Five of the six had already written down an unresolved question but did not run
the corresponding experiment. The uncertainty was present in their notes. One
conclusion was headed *IMPOSSIBILITY PROOF (within the verified model)* and
ended "unless a mechanic outside this model exists." One `lf52` agent had also
written this rule after level 4:

> Don't conclude "unsolvable/isolated" until the whole world has been swept.

Two levels later it concluded unsolvable, with 1,726 actions unspent and that
line still sitting in the notes file it re-reads whenever its memory is
trimmed. It had recorded the uncertainty but did not act on it.

[`docs/failure-modes.md`](docs/failure-modes.md) works through all fourteen
non-wins, including the failures that do not fit this pattern.

## Sandboxing

Game source and other harnesses' traces are public, so a run with ordinary
internet access could find an answer key. Each game therefore runs inside an
E2B sandbox with default-deny egress.

- Three hosts are allowed—the model API, broker, and Postgres—plus DNS. The
  rules match SNI and the Host header. [`tests/verify_fence.py`](tests/verify_fence.py)
  checks the fence live from inside a sandbox.
- The ARC game key never enters the agent's machine. [`broker.py`](rig/broker.py)
  holds it, owns the game sessions, and writes the canonical log. The agent
  receives a forwarding client with no credentials.
- A provider can browse on the caller's behalf, which the network fence cannot
  prevent. Claude's API reports server-side web use; across 191 Claude
  sessions it reported zero searches and zero fetches.
- [`audit.py`](rig/audit.py) scans each complete event stream for network
  clients, DNS probes, package installation, encoded payloads, credential
  reads, second agents, and attempts to use the model API as a browser.

## An agent tried to break out

In the latest 25-game Codex pass, 7 sessions tried to reach the internet for
help. The targets included game source on Hugging Face and GitHub, published
traces for the game being played, trajectory datasets, another harness's site,
and ARC scorecard pages. The agents tried HTTPS, HTTP, a mirror, a proxy,
`git clone`, `wget`, `urllib`, and `curl`. Across all Codex passes, 11 of 60
sessions tried it.

The fence blocked every attempt, usually during the TLS handshake:

```
urlopen error TLS/SSL connection has been closed (EOF)
curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL
fatal: unable to access '…': gnutls_handshake() failed
```

None of the 191 Claude sessions did this; the provider's web-request counter
also remained at zero.

The contrast between the models is notable: GPT-5.6-sol tried to look outside
the game for an answer, while Opus 5 did not. Because the attempts took several
forms, the result depends on prevention rather than detection after the fact.

## The record

The database holds all 251 sessions: every command, every result, each action
log, the agent's notes and programs, and per-level action counts. Under the
current audit rules, 236 are clean. The other 15 consist of the 11 Codex
answer-seeking attempts above, two agents probing their own broker while
debugging a failed connection, and two early Claude runs that used the game
key before the broker existed.

The full post-broker record will be released shortly on the
[releases page](https://github.com/jerber/arc-code/releases). It will include
the headline Claude pass, the Codex comparison, all four `lf52` attempts, the
Codex breakout attempts, and earlier passes. One earlier prompt still included
interface facts such as action names, board size, and the color map. It scored
97.3, about one point higher and within the observed variance, while using a
third more actions. Each session contains the exact prompt it ran.

The pre-broker workspaces will not be included because they contain live ARC
session cookies—the exposure the broker was written to remove.

ARC only discloses scores on closed scorecards and removes idle ones, so
[`score.py`](rig/score.py) contains a reconstruction of the metric. It
reproduces 106 of the 111 scores ARC disclosed; the five misses are documented
in the code rather than fitted away. [`export.py`](rig/export.py) builds and
verifies the release archive, and [`docs/REPRODUCE.md`](docs/REPRODUCE.md)
shows how to load it into a database once released, rerun the audit and
scorer, and check the known uncertainties.

## Credit

[PRO-LONG](https://github.com/alexisfox7/PRO-LONG) is where I got the idea to
use a log written by code and read back with grep and Python as the agent's
memory.

The human baselines in [`baselines.json`](rig/baselines.json) are ARC's own
numbers from the closed scorecards for these runs.

## License

MIT
