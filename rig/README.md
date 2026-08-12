# rig

The harness is three files at the root: [`PROMPT.md`](../PROMPT.md),
[`act.py`](../act.py), [`run.py`](../run.py). This directory is everything
holding them up — none of it knows anything about any particular game.

**Running games safely**

| | |
|---|---|
| [`cloud.py`](cloud.py) | a fenced sandbox per game; deny all egress, allow three hosts |
| [`broker.py`](broker.py) | holds the game key, so the agent's machine never has it |
| [`client.py`](client.py) | the shim the agent calls instead of the actuator |
| [`db.py`](db.py) | the record every session mirrors itself to as it plays |
| [`agents.py`](agents.py) | which CLI plays, and how to read its event stream |

**Checking the results**

| | |
|---|---|
| [`audit.py`](audit.py) | grades every trace for reaching past the game |
| [`score.py`](score.py) | ARC's metric, recomputed rather than remembered |
| [`export.py`](export.py) | the published bundle, and the gate that vets it |

`baselines.json` is ARC's own per-level human action counts for the 25 public
games, read by `score.py`.

Not a package, deliberately. A sandbox is sent these files and overwrites them
between the image build and launch, and an installed copy would shadow the
fresh one. `run.py` puts this directory on the path; the three modules that are
also run directly put the repo root on it.
