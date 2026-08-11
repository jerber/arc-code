# arc-code

Opus 5 scores
[**30.2%**](https://arcprize.org/results/anthropic-claude-opus-5) on the 25
public games of ARC-AGI-3 under ARC's model-only evaluation, the best
bare-model result on the benchmark. Hand the same model a shell, a file
system, and one command that plays the game, and it scores **96.2 on the
same games** at the same `high` reasoning effort, winning 24 of 25, for
about **$540** (pass@2: 99.3, all 25 won). Nothing I wrote closes that gap.
The harness has no solver, no world model, no planner, no grid tooling. The
model writes all of that itself, per game: first a parser, then rules, then
a simulator, then a search over the simulator. One pass produced **294
programs, ten times the size of the harness that launched them**, and every
one was thrown away when its game ended.

arc-code is the harness that lets it: stock Claude Code with almost nothing
switched on. It runs headless with six tools pre-approved (Bash, Read,
Write, Edit, Grep, Glob), no MCP servers, no subagents, no custom tools, no
plugins or hooks, and the model at its default thinking effort. Nothing is
fine-tuned and no example of a solved game is ever shown. Each game gets one
session that plays it from first action to last, with a prompt that is
method only: it never says what game is being played, or even that this is
ARC. Every action and the board it produced is appended to `logs.txt` by
code. That file, not the context window, is the agent's memory, read back
with grep and Python.

The claim this repo makes: the general-purpose harness has stopped being
where the task gets solved. Its job is to hand the model a shell, files, and
an honest log; the model writes the task-specific harness itself, at runtime,
once per game. That is meta-learning in the plainest sense, the agent
learning each game by first building the thing that learns it, and it is
the ability ARC-AGI-3 was built to measure: an agent that can ["explore novel
environments, acquire goals on the fly, build adaptable world models, and
learn continuously"](https://arcprize.org/arc-agi/3/). Some of what got built
is worth reading:
[the agent builds the machinery](#the-agent-builds-the-machinery).

Every game plays in its own sandbox that can't reach the internet, because a
lot of what's online about these games amounts to an answer key. That part is
enforced rather than trusted: [sandboxing](#sandboxing).

## The harness

- **A prompt** ([`PROMPT.md`](PROMPT.md)) that never names the environment,
  only method: parse your log instead of reading it, keep findings in files,
  probe with 1–2 actions before committing 10–20. Swap ARC-AGI-3 for another
  interactive benchmark and it travels unchanged, by construction though [not
  yet by demonstration](docs/REPRODUCE.md#what-is-uncertain-stated-plainly);
  the swap that is demonstrated is the model. What *this* environment is
  lives in an eleven-line brief ([`ARC.md`](ARC.md)) the launcher puts in
  front of it; the rest of the interface, how a board reads and what the
  log's markers mean, is documented by the actuator's log in its own opening
  lines. The prompt is left holding no game-specific fact at all.
- **An actuator** ([`act.py`](act.py)): the only way an agent touches the
  game. `./act do ACTION1 ACTION6:30,40 --plan "..."` plays actions in order,
  stops the moment one scores, and appends every action and resulting board to
  `logs.txt`, verbatim.
- **A launcher** ([`run.py`](run.py)): one agent session per game, full event
  stream recorded. Codex swaps in with one flag; nothing in the harness knows
  which model is playing.

The agent gets a shell and files. That's all.

Everything else lives in [`rig/`](rig): the fenced sandboxes, the broker that
holds the game key, the record, the audit, the scorer, and the exporter. None
of it knows anything about any particular game either; [`rig/README.md`](rig)
says what each file is for.

## Running it

Needs Python 3.13+, [uv](https://docs.astral.sh/uv/), an [E2B](https://e2b.dev)
account, a [Neon](https://neon.tech) database, and a model key. Copy
`.env.example` to `.env` and fill it in.

```bash
uv sync
uv run pytest -q                                   # 117 tests, no network
uv run rig/db.py init                                  # create the tables
uv run --with e2b rig/cloud.py build                   # bake the sandbox image

uv run --with e2b rig/cloud.py start ft09-0d8bbf25 --broker --run smoke
uv run --with e2b rig/cloud.py watch smoke             # progress, from the database
```

Swap `--agent codex` to play with Codex, or pass `$(cat docs/games.txt)` for
all 25. [`docs/REPRODUCE.md`](docs/REPRODUCE.md) has the rest.

## Results

| | Claude Code (Opus 5) | Codex (gpt-5.6-sol) |
|---|---|---|
| thinking effort | `high` (the default) | `xhigh` |
| ARC score | **96.2** | 73.7 |
| games won | **24 / 25** | 19 / 25 |
| total actions | **8,789** | 26,971 |
| cost | ~$540 | **~$424** |
| internet access | none | none |

(ARC's metric scores action-efficiency against human baselines, capped at 100
per game. Claude's cost is billed by the CLI and includes two sessions that
crashed or self-quit and were resumed; Codex reports only tokens, so its figure
is computed from published prices and is a floor. Both columns are one pass over
the 25 games, same prompt, same actuator; only the model differs.)

Neither model ran at its highest reasoning setting. Claude's `high` is just
the default, with `xhigh` and `max` above it, and Codex's `xhigh` has `max` and
`ultra` above it. I wanted to see what a general coding harness and a capable
model do close to out of the box, and that turns out to be enough to saturate
the benchmark. Turning the reasoning up is the next thing I'll try.

**pass@2 is 99.3**, with all 25 games won. The one game the first pass lost,
`lf52`, is the most interesting thing in this repo:
[when the model is certain and wrong](#when-the-model-is-certain-and-wrong).

## The agent builds the machinery

Opus 5 starts each game with a shell and an empty folder. What it does with them
is write code. It looks at a few boards, writes a Python file that reads them,
runs it, writes down what it learned, and keeps going. By the end of a game
the folder holds a small program the agent wrote to solve that one game, and a
`notes.md` recording what it had figured out.

By the end of the pass that was **294 programs, about 14,600 lines**, and all
25 games had their own. Nothing in the prompt says to do this. It names no
algorithm, and the only encouragement is one line saying shell and Python
loops are allowed.

### One game, start to finish

In `re86` you steer a cross-shaped piece around a board to cover colored boxes.
Nobody says that; [the session](data/runs/re86_v2rest20) had to work it out.

**First, see the board.** The agent's first file is `parse.py`, which reads the
log and turns a screen of pixels into a list of objects: here is a cross, here
are eight boxes, here is a bar along the bottom. Every later file is built on
this one. Until the game is a list of objects instead of a picture, nothing else
can be written.

**Then, guess the rules and write them down.** `notes.md` fills up with things
it has confirmed and things it suspects, kept separate: arrows move the active
shape three cells at a time, `ACTION5` switches which shape you're steering, and
the purple bar on the bottom row is a move counter, so there's a limit. Then a
goal hypothesis: the four boxes of each color sit in a plus pattern, and the
cross has to be centered where their arms meet.

**Then, build something that predicts.** Once it thinks it knows the rules, it
writes `sim.py`, which answers "if I press this, what does the board look like
after?" without spending an action. That's the point: actions are the scored
resource, and a simulator lets it test a hundred ideas for free.

**Then, be wrong and fix it.** Later levels bring a rectangular ring, and the
first model, `rect.py`, assumes it slides like everything else. It doesn't:
pushed into an obstacle, it *squashes*, keeping one edge and growing sideways.
So `rect2.py` replaces the sliding rule with a squeeze rule, and then `rect3.py`
gets more precise about which edge grows first. Three files, three theories, each
replacing the last when the board contradicted it. Eight of these little model
series went through three or more versions in the pass.

**Then, solve it.** With a simulator that matches reality, `route.py` and
`game.py` search: try move sequences against the simulator, throw away the ones
that fail, keep the shortest one that wins. Then run it for real.

Parse, hypothesize, simulate, correct, search, execute. Nothing told it to work
this way.

### The same shape, different games

- **`tu93`** ([session](data/runs/tu93_v2sub)): it worked out that the 64×64
  screen was really a 21×21 grid of blocks holding a maze, and that the magenta
  bar on the bottom row encoded a 50-move budget, `remaining = 64 × (1 −
  steps/50)`. Then a later level added something that hunts you, so it wrote
  `chase.py`: a "guaranteed-win search against chasers that move 1 node per
  player move."
- **`m0r0`** ([session](data/runs/m0r0_v2rest20)): two characters mirror each
  other, so moving one moves both. It took four attempts (`solve.py` through
  `solve4.py`) to land on tracking both positions at once, plus the dot and the
  mode, as a single state to search over.
- **`lf52`** ([session](data/runs/lf52_v2rest20)): the world is wider than the
  screen and scrolls. Nobody mentioned that; the agent noticed, then wrote six
  files that together keep a map: measure how far the view shifted between two
  boards, stitch the views into one map, find the walls in it, work out where the
  camera is pointing now, and correct every click for the scroll before sending
  it.
- **`ka59`**: a search that steers a box to push objects into pens, which is
  Sokoban, rediscovered without the name.

The `notes.md` files read like lab notebooks, and the agents label their
confidence without being asked: "hypothesis, strong", "confirmed so far",
"presumed", "(untested)".

Six sessions are checked into [`data/runs/`](data/runs) so you can read
them without downloading anything: the notes, the scripts, and both records, as
the agents left them. Everything else is in the published bundle. That is the
argument for a thin harness: whatever a game turns out to need, the model builds
it, and building it *is* the thing ARC-AGI-3 is trying to measure, which ARC
describes as "planning horizons, memory compression, and the ability to update
beliefs as new evidence appears."

## Other harnesses

Higher verified scores on these games belong to Tycho (100), Retrodict (99.9)
and baseline1 (99), on ARC's
[community leaderboard](https://arcprize.org/leaderboard/community), which is
where harness results live, separate from ARC's official model-only evaluation.
All of them wrap the model in machinery built for ARC-AGI-3: world-model
contracts, grid tooling, planners, replay verifiers. They're careful systems and
they score higher; I'm not claiming a rank.

Two other general-purpose harnesses are worth reading, because each takes a
different route to the same place:

- **[PRO-LONG](https://github.com/alexisfox7/PRO-LONG)**
  ([paper](https://arxiv.org/abs/2607.20064)) runs the same Claude Code CLI, and
  is where the log-as-memory idea this harness is built on comes from (credit
  below). They report **97.4% best@2 with Fable 5**. The design difference is who
  drives: their agent writes a batch of actions to a file and stops, and a runner
  plays them against the game, so the loop lives in the harness rather than in
  the agent.
- **[Prime Agent](https://www.primeintellect.ai/blog/prime-agent)** is a
  general-purpose harness Prime Intellect built from scratch: recursion over
  context, sub-agents as function calls, and harness state the agent can rewrite
  mid-task. They report **95.5% RHAE Best@1 with Opus 5**.

Put the numbers side by side and they say one thing: three general-purpose
harnesses, built independently, none carrying a line of game-specific
machinery, all land within a few points of the systems that do, while the
model underneath scores 30.2 with no harness at all, the best bare-model
result there is. Hand-building the machinery is now worth a few points.
Giving a model room to build it is worth sixty-six.

## When the model is certain and wrong

The same capacity that builds a world model can build the wrong one and trust
it. `lf52` is the one game the pass in the table lost, and the reason is worth
more than the point it cost.

It is a peg-solitaire machine ten levels deep. Level 6 introduces a red piece.
Two agents playing it (same prompt, same model, separate sandboxes) mapped
the level, wrote a simulator, searched it exhaustively, and produced a written
argument that the level is **unsolvable**: the west panel yields only one green
peg, and every maneuver that scrolls the camera forces that peg onto the wrong
column. The arithmetic was correct. One of them spent four hours and stopped
with 1,700 actions of budget unused, not because it ran out but because it
could not find a move that changed the arithmetic. It even named the two things
its model might be missing, and did not go back to test them.

Two other agents, cold, on the identical game, found the missing thing: the red
piece is a **mobile wall**: it leapfrogs a green peg without capturing it, and
a red-green pair walks a lone peg anywhere on the board. Column parity dissolves,
the "unsolvable" level falls in ~130 actions, and the game is won 10/10. Across
four attempts, `lf52` solved twice.

So the failure mode of a strong agent is not flailing. It is a valid proof over
an incomplete model. The more capable the agent, the more convincing the proof,
and the less likely it is to go back and re-question what the pieces on the board
actually *are*. The prompt already says to (*"your model is probably wrong rather
than incomplete… re-derive what the things in front of you are"*); the agents
that quit had read it and reasoned past it. The proofs and the breakthroughs are
both in the record, verbatim.

## Sandboxing

Plenty on the internet about these games amounts to a solution: game source
files, other harnesses' published traces. So every run is fenced:

- **Each game plays in its own [E2B](https://e2b.dev) sandbox**, default-deny
  egress: three hosts allowed (model API, broker, Postgres) plus DNS, matched
  exactly by SNI and Host header. Verified live from inside
  ([`tests/verify_fence.py`](tests/verify_fence.py)).
- **The game key never enters the agent's machine.** A broker sandbox
  ([`broker.py`](rig/broker.py)) holds it, owns every game session, and writes the
  canonical log; the agent gets a tiny forwarding client and no credentials.
- **The model API is the one hole a fence can't close**: providers will
  browse on a caller's behalf. For Claude, the API reports a server-side
  web-request counter nothing in the sandbox can shade: **zero searches, zero
  fetches across all 191 Claude sessions.**
- **Every session is audited** ([`audit.py`](rig/audit.py)): the full event stream
  is scanned for network clients, DNS probes, package installs, encoded
  payloads, credential reads, second agents, and use of the model API as a
  browser.

## An agent tried to break out

**Codex, under pressure, goes looking for answers.** In the most recent 25-game
Codex pass, **7 of the 25 sessions** tried to reach the internet for a shortcut:
the game's own source on HuggingFace and GitHub, other harnesses' published
traces for the exact game being played (baseline1's repo, trajectory datasets,
a rival harness's site), even ARC's own scorecard pages, via HTTPS, plain HTTP,
a mirror domain, a proxy service, `git clone`, `wget`, `urllib` and `curl` in
turn. Across every Codex pass it is **11 of 60 sessions**. **Every attempt
returned nothing**, most dying at the TLS handshake:

```
urlopen error TLS/SSL connection has been closed (EOF)
curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL
fatal: unable to access '…': gnutls_handshake() failed
```

Claude did this **zero times in 191 sessions**, and there the provider's own
web-request counter, not just my audit, is the evidence: zero.

I had assumed nothing pushes on the audit: an agent only wants to win the
game. That was wrong, and it got more wrong as the models got a longer leash:
the rate of a capable agent trying to find the answer rather than derive it went
*up*, not down. It will be creative about how. Measure behind a boundary the
agent cannot cross; detection alone is not enough.

## The record

All **251 sessions** are stored: every command run, every result seen, plus
each game's log, notes, and per-level action counts. Re-graded under stricter
rules than they were originally judged by, **236 came back clean**. Of the 15
findings, 11 are the Codex answer-seeking above, two are agents probing their
own broker while diagnosing a flaky connection (benign; the broker fails
closed and returned nothing), and two are early Claude sessions that used the
game key from before the broker existed, which is why it exists.

Everything from the broker onward is published, a 42 MB archive on
the [releases page](https://github.com/jerber/arc-code/releases), built by
[`export.py`](rig/export.py): the pass above, the whole Codex comparison, the
`lf52` attempts with their impossibility proofs and their breakthroughs, every
Codex breakout attempt, and the earlier passes, including a 97.3 from a
prompt draft that still carried the interface facts (action names, board size,
color map), since moved into the brief and the log. That one is a point
higher, well inside the variance, and took a third more actions; each session
embeds the exact prompt it ran. The runs that predate the broker are held
back because their workspaces hold live ARC session cookies, the exposure
the broker was built to end; the two Claude findings live in those runs.

ARC discloses scores only on closed scorecards and reaps idle ones, so the
scoring formula lives here ([`score.py`](rig/score.py)) and reproduces the
official scores ARC did disclose, with every miss documented in code rather
than fitted around. To take none of it on my word, download the bundle,
verify it, and load it into a Postgres of your own; `score.py` and
`audit.py` then run against your copy.
[`docs/REPRODUCE.md`](docs/REPRODUCE.md) has the sequence and the
uncertainties, stated plainly.

## Credit

[PRO-LONG](https://github.com/alexisfox7/PRO-LONG) is where I got the idea that
an agent's memory should be a log written by *code* and read back with grep and
Python, the idea this whole harness is built around.

Human baselines in [`baselines.json`](rig/baselines.json) are ARC's own numbers,
from the closed scorecards of these runs.

## License

MIT
