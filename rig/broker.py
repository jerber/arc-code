#!/usr/bin/env python3
"""The actuator, moved out of the agent's reach.

`act.py` is the only thing allowed to touch the game, and until now it ran
inside the agent's own sandbox — which put the game key and the live session
cookies on a disk the agent is root on. One run proved that is not a boundary:
handed a session that might have died, an agent read `scorecard.json`, built
its own HTTP client with `ARC_API_KEY` and played a RESET that never reached
`logs.txt`.

So `act.py` runs here instead. This process holds the key and every game
session, plays through the same actuator, and writes the log. The agent gets a
small forwarding client and no key at all — ARC answers 401 to every endpoint
without one, so there is no request it can make on its own.

The guarantee is *not* that the agent uses the provided client. It may call this server
directly, and it must be able to, because that is how it plays. The guarantee
is that anything reaching the game is written down by the thing that forwards
it. Bypassing the client desynchronises the agent's own copy of the log and
achieves nothing else, and the audit sees that as a diff against this one.

    ARC_API_KEY=... ARCSEC_TOKEN=... ARCSEC_RUN=night uv run broker.py
"""

import hmac
import json
import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Run directly as well as imported, so the repo root has to be on the path
# before `act` is imported. rig/ is not a package: a sandbox overwrites these
# files between the image build and launch, and an installed copy would
# shadow the fresh one.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db

from act import LOG, SCORECARD, Scorecard
from act import STATE as STATE_FILE

REPO = Path(__file__).resolve().parents[1]
ACT = REPO / "act.py"
WORK = Path(os.environ.get("ARCSEC_WORK", "/broker"))
PORT = int(os.environ.get("ARCSEC_PORT", "8000"))
RUN = os.environ.get("ARCSEC_RUN")  # names the rows this writes to Postgres

# One game is one agent playing serially, so contention is unlikely — but two
# requests inside one workspace would interleave act.py's read-modify-write of
# state.json, and the log with it.
LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)
CARD: list[Scorecard] = []  # the batch's one scorecard, opened on first use
# Which games this batch is waiting for, and which have reported in. ARC reaps
# an idle card after fifteen minutes, so the card has to close the moment the
# last game ends — not whenever someone next looks. A sweep lost its official
# score to exactly that gap: the last game finished, nothing closed the card,
# and half an hour later it was gone.
GAMES = [g for g in os.environ.get("ARCSEC_GAMES", "").split(",") if g]
DONE: set[str] = set()
# Reporting in is not enough on a large batch. The reaper counts from the last
# *action*; a session keeps running long after its last one, writing notes and
# its report, and on twenty-five games there is always a straggler. Both 25-game
# sweeps lost their cards that way while every batch of five kept its own.
#
# So the card also closes on idleness: no action anywhere for this long, and
# every game in a state it cannot act from again. Both conditions are needed —
# the second is what stops a card closing under a session that is merely
# thinking, whose next action would then fail.
# `or` rather than a default: an unset variable and one passed through empty
# must mean the same thing. They did not, and the broker died on startup.
IDLE_CLOSE = int(os.environ.get("ARCSEC_IDLE_CLOSE") or 10 * 60)
TERMINAL = ("WIN", "GAME_OVER")
ACTED: list[float] = [time.time()]  # when anything last played
STATE: dict[str, str] = {}  # game -> the state its last action returned


def spent(game: str) -> bool:
    """Whether this game will ever act again.

    Three ways to be sure it will not: it won, it lost, or its session has
    reported in and ended. The third matters most — a session that stopped with
    budget left is neither WIN nor GAME_OVER, and without counting it a single
    such game would hold the card open until the reaper took it. That is the
    likeliest reason both 25-game sweeps lost their scores while every small
    batch kept its own.
    """
    return game in DONE or STATE.get(game, "") in TERMINAL


def should_close(now: float, last_action: float, games: list[str], idle: int) -> bool:
    """Whether the card should close, given only facts and a clock.

    Kept pure so the rule can be tested without a card, a sandbox or a wait.
    """
    if not games:
        return False
    if now - last_action < idle:
        return False
    return all(spent(game) for game in games)


def watchdog() -> None:
    while True:
        time.sleep(30)
        try:
            if CARD and should_close(time.time(), ACTED[0], GAMES, IDLE_CLOSE):
                print(
                    f"watchdog: {int(time.time() - ACTED[0])}s idle, every game spent — closing",
                    flush=True,
                )
                close_card()
                return
        except Exception as exc:  # a watchdog that dies silently is worse than none
            print(f"watchdog: {type(exc).__name__}: {exc}", flush=True)


def scorecard() -> Scorecard:
    """One card for the batch, so a game left thinking does not idle out the
    card that every other game is still playing onto."""
    if not CARD:
        CARD.append(Scorecard.open(tags=["arc-code"]))
        print(f"scorecard {CARD[0].card_id}", flush=True)
    return CARD[0]


def play(game: str, argv: list[str]) -> dict[str, object]:
    """Run one act.py command in this game's workspace and report what it did.

    The log delta is taken by byte offset around the call rather than tracked
    in memory: it is then exact whatever act.py wrote, and survives a restart
    of this process.
    """
    ws = WORK / game
    with LOCKS[game]:
        ws.mkdir(parents=True, exist_ok=True)
        # A game needs a card, and only the first game to ask opens one —
        # act.py finds it here and every other game joins the same one.
        if argv[:1] == ["init"] and not (ws / SCORECARD).exists():
            scorecard().save(ws)
        log = ws / LOG
        before = log.stat().st_size if log.exists() else 0
        done = subprocess.run(  # noqa: S603
            [sys.executable, str(ACT), *argv], cwd=ws, capture_output=True, text=True
        )
        after = tail(game, before)
        ACTED[0] = time.time()
        state = json.loads((ws / STATE_FILE).read_text()) if (ws / STATE_FILE).exists() else {}
        STATE[game] = str(state.get("state", ""))
        if state.get("actions_used", 0) >= state.get("max_actions", 1 << 30):
            STATE[game] = "GAME_OVER"  # budget gone is as final as a loss
        if RUN:
            # State and actions only. The agent's own workspace — its notes, its
            # scripts, its mirror of the log — is uploaded by the launcher, and
            # both writing artifacts would have them overwrite each other.
            # Only the new bytes are parsed: this runs after every action, for
            # every game in the batch, against a log that grows all run.
            db.push_state(RUN, game, ws)
            db.push_slice(RUN, game, after["log"])
        return {"stdout": done.stdout + done.stderr, "rc": done.returncode, **after}


def tail(game: str, offset: int) -> dict[str, object]:
    """The canonical log from a byte offset, and how long it now is.

    Bytes throughout: a text-mode seek to an arbitrary offset is not defined,
    and the client counts its mirror in bytes too. `size` is what lets a client
    notice its copy has fallen behind and ask for the rest.
    """
    log = WORK / game / LOG
    if not log.exists():
        return {"log": "", "size": 0}
    with log.open("rb") as handle:
        handle.seek(offset)
        body = handle.read()
    return {"log": body.decode(errors="replace"), "size": offset + len(body)}


def workspaces() -> list[str]:
    """The games this broker holds — directories, not whatever else is lying
    about in the work root."""
    return [p.name for p in WORK.iterdir() if p.is_dir()]


def finished(game: str) -> dict[str, object]:
    """A game reporting that its session has ended.

    The broker cannot tell a finished game from a thinking one — a session can
    stop with most of its budget unspent — so the launcher says so, and the card
    closes as soon as the last one has.
    """
    DONE.add(game)
    waiting = sorted(set(GAMES) - DONE)
    if GAMES and not waiting:
        return close_card()
    return {"closed": False, "waiting": waiting}


CLOSED: list[bool] = [False]


def close_card() -> dict[str, object]:
    """Close the batch's card and keep ARC's own scoring of it.

    Closing is the only way to get those numbers, and a closed card is dropped
    immediately — so they are written to the database here, while they exist.

    Idempotent, because two things now close cards: the last game reporting in,
    and the watchdog. Whichever is first wins and the other is a no-op — asking
    ARC to close a card it has already dropped would only raise.
    """
    if not CARD:
        return {"closed": False, "why": "no card was opened"}
    if CLOSED[0]:
        return {"closed": True, "card_id": CARD[0].card_id, "why": "already closed"}
    # Marked closed only once ARC has actually closed it. Setting the flag first
    # cost a run its scorecard: the close threw, the flag was already set, and
    # every later attempt — the watchdog's and a manual one — reported success
    # without retrying. A failed close has to stay retryable.
    official = CARD[0].close()
    CLOSED[0] = True
    if RUN:
        db.record_official(
            RUN, sorted(workspaces()), CARD[0].card_id, official
        )
    print(f"closed {CARD[0].card_id}: {official.get('score')}", flush=True)
    return {"closed": True, "card_id": CARD[0].card_id, "official": official}


class Handler(BaseHTTPRequestHandler):
    def reply(self, code: int, body: dict[str, object]) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def allowed(self) -> bool:
        """The token stops strangers reaching a public URL. It is not a
        restraint on the agent, which must hold it in order to play.

        No unset-means-open branch: this process holds the game key and listens
        on a public address, so a missing token would make it an open proxy onto
        someone else's ARC account. main() refuses to start without one.
        """
        want = os.environ.get("ARCSEC_TOKEN", "")
        got = self.headers.get("Authorization", "")
        # An empty token would otherwise match the literal header "Bearer ",
        # which is the open-proxy case main() also refuses to start in.
        if want and hmac.compare_digest(got, f"Bearer {want}"):
            return True
        self.reply(401, {"error": "bad token"})
        return False

    def do_POST(self) -> None:  # noqa: N802
        if not self.allowed():
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        path = urlparse(self.path).path
        game, argv = body.get("game"), body.get("argv")
        # Every branch inside the guard: ActError is a SystemExit, which is not
        # an Exception, and uncaught it kills the connection instead of
        # answering with the reason. A failing close reported itself as a bare
        # 502 for that reason, which cost an hour of guessing at the cause.
        try:
            if path == "/close":
                return self.reply(200, close_card())
            if path == "/done":
                if not game:
                    return self.reply(400, {"error": "need game"})
                return self.reply(200, finished(game))
            if path != "/act":
                return self.reply(404, {"error": "no such endpoint"})
            if not game or not isinstance(argv, list):
                return self.reply(400, {"error": "need game and argv"})
            self.reply(200, play(game, [str(a) for a in argv]))
        except (Exception, SystemExit) as exc:
            self.reply(500, {"error": f"{type(exc).__name__}: {exc}"})

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path == "/health":
            return self.reply(200, {"ok": True, "games": sorted(workspaces())})
        if not self.allowed():
            return
        if url.path != "/log":
            return self.reply(404, {"error": "no such endpoint"})
        query = parse_qs(url.query)
        game = (query.get("game") or [""])[0]
        offset = int((query.get("offset") or ["0"])[0])
        self.reply(200, tail(game, offset)) if game else self.reply(400, {"error": "need game"})

    def log_message(self, *args: object) -> None:
        """One line per request, on stdout with everything else."""
        print(f"{self.command} {self.path} {args[1] if len(args) > 1 else ''}", flush=True)


def main() -> int:
    if not os.environ.get("ARC_API_KEY"):
        raise SystemExit("broker: ARC_API_KEY is not set — it is the whole point of this process")
    if not os.environ.get("ARCSEC_TOKEN"):
        raise SystemExit(
            "broker: ARCSEC_TOKEN is not set — this process holds the game key and "
            "listens on a public address, so it will not start without one"
        )
    WORK.mkdir(parents=True, exist_ok=True)
    print(f"broker on :{PORT}, workspaces in {WORK}, run {RUN or '(not recording)'}", flush=True)
    print(f"watchdog: closing after {IDLE_CLOSE}s idle with every game spent", flush=True)
    threading.Thread(target=watchdog, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())
