# Six sessions, as the agents left them

The [bundle](https://github.com/jerber/arc-code/releases) is the complete
record — 171 sessions. These six are the ones the [README](../README.md) points
at, copied out so you can read them without downloading a gigabyte.

Each folder is one session's workspace, flat, exactly as the agent left it:
`notes.md` and the `.py` files it wrote, `logs.txt.gz` (every action and the
board it produced, written by `act.py`), `agent_stream.jsonl.gz` (every message,
command and result, written by the CLI), `report.json` (cost, turns, tokens,
audit verdict), and `CLAUDE.md` — the exact prompt that session ran. Folders are
named `game_run`, so each one is `artifacts/<run>/<game>/` in the bundle and
diffs against it byte for byte. Nothing is edited; the only changes are the
scrub every published artifact gets (thinking signatures blanked, sandbox
hostnames generalised) and gzip on the two large records.

| folder | what it shows |
|---|---|
| [`lf52_v2rest20`](lf52_v2rest20) | The impossibility proof. This session mapped level 6, built a simulator and a planner, searched exhaustively, and concluded the level was unsolvable — then stopped with two thirds of its budget unspent. `notes.md` has the argument; `mine.py` → `wbuild.py` → `world.py` → `wparse.py` → `state.py` → `drive.py` is the mapping-and-localisation stack it wrote after noticing the camera scrolls. |
| [`lf52_lf52-r1`](lf52_lf52-r1) | The same game, cold, won 10/10 in 840 actions. `notes.md` has the section the other two missed: the red piece is a *mobile wall* that leapfrogs a peg without capturing it, which makes column parity irrelevant. Level 6 fell in 129 actions. |
| [`lf52_lf52-r3`](lf52_lf52-r3) | The second wrong proof, independently arrived at. Ends: *"I stopped with budget remaining because I could not find any action sequence that changes that arithmetic… If there's a seventh mechanic in this level, I didn't find it."* There was. |
| [`re86_v2rest20`](re86_v2rest20) | Belief revision on disk. `rect.py` models the shapes as translating; `rect2.py` replaces it after contradicting evidence — they *squeeze* against obstacles; `rect3.py` (labelled v4 inside) pins down which end grows first. Also `sim.py` and `game.py`, the parse → assignment → routes pipeline. |
| [`tu93_v2sub`](tu93_v2sub) | Perception, then adversaries. `notes.md` decodes the 64×64 field into a 21×21 block grid holding a maze, and reads the magenta bar on the bottom row as a step budget — `remaining = 64 × (1 − steps/50)`, so 50 moves per level. `maze.py` extracts and searches it; `chase.py` is what it wrote once the level added a hostile that moves when you do: *"guaranteed-win search against chasers that move 1 node per player move."* |
| [`m0r0_v2rest20`](m0r0_v2rest20) | State-space design. `solve4.py` is a BFS over `(avatarL, avatarR, dot, mode)`, a space the agent defined after working out that two avatars mirror each other. `solve.py` through `solve4.py` are the four attempts it took to get there. |

To read a compressed record:

```bash
zcat data/runs/lf52_lf52-r1/logs.txt.gz | head -40
zcat data/runs/lf52_lf52-r1/agent_stream.jsonl.gz | jq -r 'select(.type=="assistant")' | head
```

To copy out a different session, from the bundle loaded into your own Postgres:

```bash
uv run rig/export.py pick tu93@v2sub --out data/runs
```
