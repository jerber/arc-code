#!/usr/bin/env python3
"""`act`, as the agent sees it — a shim with no key and no game behind it.

Everything is forwarded to the broker, which holds ARC_API_KEY, owns the game
session and writes the log. What comes back is that command's output and the
bytes the broker appended to the canonical log; those are mirrored here so the
log can still be grepped locally, which is the whole method.

The mirror is a convenience, not the record. If it falls behind — because the
log was edited, or because the broker was called without going through this —
the size the broker reports will not match, and the rest is fetched. What the
broker wrote is what happened.

Standard library only: this runs in a sandbox that has nothing else.
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Read when used rather than at import, so a missing one is a clear error from
# the command the agent ran and not a traceback before anything has happened.
GAME = os.environ.get("ARCSEC_GAME", "")
LOG = "logs.txt"
TIMEOUT = 600  # a batch of actions against a slow game is still one call


def broker() -> str:
    where = os.environ.get("ARCSEC_BROKER", "").rstrip("/")
    if not where or not GAME:
        raise SystemExit("act: ARCSEC_BROKER and ARCSEC_GAME must be set")
    return where


def call(path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        f"{broker()}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ.get('ARCSEC_TOKEN', '')}",
            "Content-Type": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"act: broker returned {exc.code}: {exc.read()[:300].decode()}") from exc
    except OSError as exc:
        raise SystemExit(f"act: broker unreachable: {exc}") from exc


def mirror(reply: dict) -> None:
    """Append what the broker wrote, and catch up if this copy has fallen behind."""
    with open(LOG, "a") as log:
        log.write(reply.get("log", ""))
    size = reply.get("size")
    here = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    if size is not None and here != size:
        rest = call(f"/log?game={GAME}&offset={here}")
        with open(LOG, "a") as log:
            log.write(rest.get("log", ""))


def main() -> int:
    reply = call("/act", {"game": GAME, "argv": sys.argv[1:]})
    mirror(reply)
    sys.stdout.write(reply.get("stdout", ""))
    return int(reply.get("rc", 0))


if __name__ == "__main__":
    sys.exit(main())
