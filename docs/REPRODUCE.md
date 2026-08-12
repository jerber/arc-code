# Reproducing the results

The [README](../README.md) says what was found; this says how to run and check
all of it. Every number in the README comes out of the commands below, from
the stored record rather than from anyone's memory.

There are two ways to reproduce this work. The release bundle reproduces the
exact numbers reported in the README. You can also run the full experiment
from scratch with your own keys and the same models, prompt, and 25 game
versions. Fresh runs are nondeterministic, so they test whether the result
replicates rather than promising the same decimal score.

## Setup

Needs Python 3.13+, [uv](https://docs.astral.sh/uv/), and an
[E2B](https://e2b.dev) account. Copy `.env.example` to `.env` and fill it in —
`.env` is gitignored and never committed:

```
ANT_API_KEY=sk-ant-...        # or OPENAI_API_KEY to play with Codex
ARC_API_KEY=...               # from three.arcprize.org
E2B_API_KEY=e2b_...
POSTGRES_DSN=postgres://...   # a Neon database; the run record
```

`db.py` talks to Postgres over Neon's HTTP SQL endpoint rather than on port
5432, so the DSN has to be a [Neon](https://neon.tech) one (the free tier is
enough). That is what lets a sandbox write its own record without a database
driver or an open port.

```bash
uv sync
uv run pytest -q                       # no network needed
uv run rig/db.py init                      # create the tables
uv run --with e2b rig/cloud.py build       # bake the image: node, both CLIs, uv, venv
```

## Playing

Each game gets its own sandbox, fenced off the internet, with one broker per
batch holding the game key:

```bash
uv run --with e2b rig/cloud.py start ft09-0d8bbf25 --broker --run smoke
uv run --with e2b rig/cloud.py watch smoke          # progress, from the database
uv run --with e2b rig/cloud.py stop smoke           # close the card, free the sandboxes
```

All 25 public games — what the README's tables are:

```bash
uv run --with e2b rig/cloud.py start $(cat docs/games.txt) --broker --run mine
```

Add `--agent codex` to play with Codex instead. `--effort` sets the thinking
effort for the whole batch; unset leaves each CLI's own default. The Claude
passes all ran at Opus 5's default, `high`; the Codex pass was launched with
`--effort xhigh`, which is not its ceiling — `max` and `ultra` sit above it.
The max-effort ablation used Claude's `max`.

The fence itself can be exercised directly — it creates a fenced sandbox and
asks it, live, to reach hosts it must refuse and hosts it must not:

```bash
uv run --with e2b --with python-dotenv tests/verify_fence.py
```

## Checking the results

Nothing depends on a sandbox surviving: every game writes itself to Postgres
as it plays, so the record is complete even for runs whose machines are long
gone.

Once the release bundle is available, start from it. It will carry the record's
own tables and every included session's workspace, so the verification commands
work against a database you control rather than mine:

```bash
export POSTGRES_DSN=postgres://...     # a Neon database of your own
uv run rig/db.py init                      # create the tables
uv run rig/export.py verify <bundle>       # scan it yourself before trusting it
uv run rig/export.py load <bundle>         # put the record into your database
```

Then:

```bash
uv run rig/db.py ls                        # every run in the bundle
uv run rig/db.py show v2rest20             # one run, game by game
uv run rig/score.py verify                 # the formula against every official score present
uv run rig/score.py best v2sub v2rest20 lf52-r1   # 99.3, the README's pass@2
uv run rig/score.py run sealed3            # 97.3, an earlier draft's pass
uv run rig/audit.py record                 # re-grade every session's trace
```

The release bundle will include the pass the README reports (`v2sub` +
`v2rest20`), the `lf52` retries, the Codex pass (`codex-v2`), the earlier-draft
passes including `sealed3`, the older Codex comparison, and `maxeffort`. Once
loaded, `score.py verify` checks every official score the bundle carries, and
`audit.py record` re-grades every included session.

The pre-broker runs will not be included: their workspaces hold live ARC
session cookies, which is exactly the exposure the broker was built to end.

`db.py pull` restores each game's workspace: `logs.txt` (the programmatic
memory — every action and its result), `agent_stream.jsonl` (the agent's
complete event stream: every command it ran, every file it wrote),
`notes.md`, any scripts the agent wrote, and `report.json` (cost, turns,
tokens, audit verdict).

## What is uncertain, stated plainly

**None of the three `sealed` passes has an official receipt.** ARC discloses a
score only when a scorecard is closed, and reaps a card that goes fifteen
minutes without an action. `sealed`, `sealed2` and `sealed3` all lost their
cards that way — `sealed3`'s to a close that failed while being marked done,
which is the bug the broker's watchdog now retries. So that draft's 97.3, the
two broker-validation numbers, and both halves of the draft prompt's 99.9
pass@2 are reconstructions by the formula in `score.py`, not numbers ARC
handed back.

**The formula is validated elsewhere, not on those passes.** `score.py verify`
reproduces 81 of the 84 game scores ARC *has* disclosed — from my own
per-level action counts and ARC's human baselines, not by reading ARC's answer
back. Every one of the 81 agrees to twelve decimal places. The three misses
are documented at `score.py`'s `UNEXPLAINED`: two are the same game whose
published total contradicts its own published per-level scores, and one is a
game that died and was retried, where my record cannot see the run boundary
ARC recorded.

**Finished games reconstruct exactly; unfinished ones do not.** 24 of the 25
games in the headline pass were won, and those are exact. The 25th (`lf52`,
5 of 10 levels) is an unfinished game of exactly the class `score.py` documents
as unreliable — a `sk48`-sized miss would move 96.2 by about a quarter point,
the worst death-boundary miss ever observed by about 1.4. The 24/25 wins are
unaffected either way.

**The metric caps at 100 per game.** Efficiency past the human baseline earns
nothing, so a high score mostly means "won nearly everything, without gross
waste". The durable claim is 24/25 games with no internet and no game-specific
knowledge, not the decimal.

**Thinking effort is configuration, not a recorded fact.** Neither CLI writes
its reasoning-effort setting into the event stream, so "Claude at `high`" and
"Codex at `xhigh`" are what the launcher was given, not something the stored
traces can prove. Unset `ARCSEC_EFFORT` means each CLI's own default, which is
`high` for Opus 5.

**Codex's cost is an estimate.** Claude Code reports its own spend; Codex
reports tokens only, so its dollar figure is computed in `agents.py` from
published per-token prices. It is a floor: requests over 272K input tokens
bill at a premium the model doesn't apply.

**The human baselines are ARC's.** `baselines.json` is extracted from the
closed scorecards ARC returned for these runs. Every card that discloses a
game's baselines agrees with every other, so they are treated as a property of
the game and committed.

**Comparison scope.** The 96.2 is one harness's single pass. Higher scores on
the same 25 public games are published on ARC's community leaderboard —
Tycho at 100.0, Retrodict at 99.9, baseline1 at 99.0 — and the set is
saturating. What this repo is measuring is how small and general a harness can
be while still scoring in that range, not a claim to the top of it.

**"General-purpose" is demonstrated across models, asserted across tasks.**
Nothing in the prompt or the rig names the environment, and Codex swaps in
with one flag; that half is tested. The other half is not: this harness has
only ever been pointed at ARC-AGI-3, so "swap the benchmark and the prompt
travels unchanged" is a design claim awaiting a second environment.
