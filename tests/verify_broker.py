#!/usr/bin/env python3
"""End-to-end check of a brokered run, against the live thing.

The unit tests cover the pieces; this asserts the whole chain held on a real
run: that the agent never had the key, that the log it read matches the one the
broker wrote, that the database agrees with both, and that ARC's own scoring
came back. Run it after a `cloud.py start --broker` batch has finished.

    uv run --with e2b tests/verify_broker.py <run>
"""

import base64
import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cloud
import db

FORBIDDEN = ("ARC_API_KEY", "state.json", "scorecard.json", "act.py")


def check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{f' — {detail}' if detail else ''}")
    return ok


def main() -> int:
    run = sys.argv[1]
    cloud.secrets()
    passed = []

    found = cloud.broker_of(run)
    if not found:
        raise SystemExit(f"verify: no broker for {run} — it may already have been stopped")
    broker, _, _ = found

    print(f"\n{run}: the agent's side")
    for game, sandbox in cloud.sandboxes(run):
        env = sandbox.commands.run("env", timeout=60).stdout
        passed.append(check(f"{game}: no game key in the environment", "ARC_API_KEY" not in env))
        listing = sandbox.commands.run(f"ls {cloud.WORK}/runs/{run}/{game}/", timeout=60)
        held = listing.stdout.split()
        leaked = [f for f in held if f in FORBIDDEN]
        passed.append(
            check(f"{game}: workspace holds no actuator or session", not leaked, str(leaked))
        )

    print(f"\n{run}: the record")
    for game, sandbox in cloud.sandboxes(run):
        theirs = sandbox.commands.run(
            f"md5sum < {cloud.WORK}/runs/{run}/{game}/logs.txt", timeout=120
        ).stdout.split()[0]
        canon = broker.commands.run(f"md5sum < /broker/{game}/logs.txt", timeout=120)
        ours = canon.stdout.split()[0]
        passed.append(check(f"{game}: agent's mirror matches the canonical log", theirs == ours))

        row = db.sql(
            "select state, score, actions_used, audit from games where run=$1 and game=$2",
            run,
            game,
        )[0]
        rows = db.sql(
            "select count(*)::int n from actions where run=$1 and game=$2 and action<>'INITIAL'",
            run,
            game,
        )[0]["n"]
        passed.append(
            check(
                f"{game}: database action count matches the game's own",
                rows == row["actions_used"],
                f"{rows} rows vs {row['actions_used']} played",
            )
        )
        passed.append(check(f"{game}: audit clean", not (row["audit"] or {}).get("findings")))

        stored = db.sql(
            "select encode(body,'base64') b from artifacts"
            " where run=$1 and game=$2 and name='logs.txt'",
            run,
            game,
        )
        if stored:
            body = gzip.decompress(base64.b64decode(stored[0]["b"]))
            played = len(db.parse_log_text(body.decode(errors="replace"))) - 1
            passed.append(
                check(f"{game}: stored artifact parses to the same actions", played == rows)
            )

    print(f"\n{run}: ARC's own verdict")
    official = db.sql(
        "select game, official->>'score' s from games where run=$1 and official is not null", run
    )
    passed.append(check("scorecard closed and its score recorded", bool(official), str(official)))

    print(f"\n{sum(passed)}/{len(passed)} checks passed")
    return 0 if all(passed) else 1


if __name__ == "__main__":
    sys.exit(main())
