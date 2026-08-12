#!/usr/bin/env python3
"""Prove the shipped tree runs, in a real sandbox.

    uv run --with e2b --with python-dotenv tests/verify_sandbox.py

`tests/test_payload.py` reconstructs the payload in a temp directory and imports
it, which catches a file at the wrong depth. It cannot catch the things that
only exist in E2B: whether `files.write` creates the `rig/` directory on the way
in, whether the baked venv still resolves, and whether a stale copy of a module
is sitting at the work root from an older image.

That last one is the reason this exists. The image used to bake the sources as
well as the environment, and a flattened `rig/db.py` at the work root is a
module `import db` finds before the fresh one the launcher writes — a stale
harness that looks exactly like a working one.

Cheap: one sandbox, a few seconds of it, no game and no model call.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rig"))

import cloud  # noqa: E402

CHECKS = {
    # the modules a session starts from, imported the way run.py imports them
    "the harness imports": (
        f"cd {cloud.WORK} && uv run python -c "
        "'import run, act, db, agents, audit, broker; print(\"ok\")'"
    ),
    # nothing from rig/ may also sit at the work root. An older image baked the
    # sources flat, and a leftover db.py there is a module that `import db`
    # could find instead of the fresh one — a stale harness that looks working.
    "no flattened copies": (
        f"cd {cloud.WORK} && ! ls db.py agents.py audit.py broker.py client.py 2>/dev/null"
        " && echo ok"
    ),
    # and the modules the harness loads come from rig/, once run.py has set the
    # path up the way a session does
    "modules resolve to rig": (
        f"cd {cloud.WORK} && uv run python -c "
        "'import run, db, agents;"
        ' assert "/rig/" in db.__file__, db.__file__;'
        ' assert "/rig/" in agents.__file__, agents.__file__; print("ok")\''
    ),
    # the entry points a run actually invokes
    "run.py answers": f"cd {cloud.WORK} && uv run run.py --help >/dev/null && echo ok",
    "act.py answers": f"cd {cloud.WORK} && uv run act.py --help >/dev/null && echo ok",
    "the record answers": f"cd {cloud.WORK} && uv run rig/db.py --help >/dev/null && echo ok",
    # the venv was baked at image build and must not need an index at runtime,
    # which a fenced sandbox could not reach anyway
    "the venv is baked": (
        f"cd {cloud.WORK} && uv run python -c 'import arcengine, pydantic; print(\"ok\")'"
    ),
}


def main() -> int:
    keys = cloud.secrets("claude")
    sandbox = cloud.Sandbox.create(
        template=cloud.TEMPLATE,
        timeout=600,
        metadata={"run": "verify-sandbox"},
        network=cloud.fence(cloud.MODEL_HOST["claude"], cloud.host_of(keys["POSTGRES_DSN"])),
    )
    print(f"sandbox {sandbox.sandbox_id}")
    try:
        for name in cloud.PAYLOAD:
            sandbox.files.write(f"{cloud.WORK}/{name}", (cloud.REPO / name).read_text())
        print(f"wrote {len(cloud.PAYLOAD)} payload files\n")

        listing = sandbox.commands.run(f"ls {cloud.WORK} {cloud.WORK}/rig", timeout=60).stdout
        print(listing.strip(), "\n")

        ok = True
        for label, command in CHECKS.items():
            got = sandbox.commands.run(f"{command} 2>&1; echo ' exit='$?", timeout=180)
            out = " ".join((got.stdout or "").split())
            passed = out.endswith("exit=0")
            print(f"  {'pass' if passed else 'FAIL'}  {label:22} {out[-140:]}")
            ok &= passed
    finally:
        sandbox.kill()

    print("\nthe shipped tree runs" if ok else "\nthe shipped tree is BROKEN — see FAIL above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
