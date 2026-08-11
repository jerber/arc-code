#!/usr/bin/env python3
"""Launch coding-agent sessions to play ARC-AGI-3 games.

One game is one long session with its own workspace: the prompt, the log it
writes, and the notes it keeps. Games are independent, so they run concurrently.

Each session's stream is recorded verbatim to ``agent_stream.jsonl`` — it is
both the trace to debug from and the source of the cost figures.
"""

import argparse
import asyncio
import json
import os
import shutil
import socket
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from pydantic import BaseModel

REPO = Path(__file__).resolve().parent
# The harness is three files; everything holding it up lives in rig/, which is
# not a package so that a sandbox can overwrite any of it between builds.
sys.path.insert(0, str(REPO / "rig"))

import db  # noqa: E402
from agents import AGENTS  # noqa: E402
from audit import Audit, audit_session  # noqa: E402

from act import DEFAULT_BUDGET, Scorecard  # noqa: E402

RUNS = REPO / "runs"
MODEL = "claude-opus-5"
TASK = (
    "Read CLAUDE.md, then play the game with ./act until `./act status` reports "
    "WIN or the action budget is spent. Work autonomously and do not stop to ask "
    "questions."
)
RESUME_TASK = (
    "A previous session playing this game was interrupted. Its workspace is "
    "yours: read CLAUDE.md, then recover what it had established from notes.md "
    "and logs.txt before acting. Continue with ./act until `./act status` "
    "reports WIN or the action budget is spent. Work autonomously and do not "
    "stop to ask questions."
)
STREAM_LIMIT = 1 << 22  # single stream-json lines can be large

# A run is only evidence if the agent played the game rather than looked up the
# answer. Withholding the web tools is not enough — Bash can reach anything — so
# every session is read back afterwards for the things that would invalidate it.
class Report(BaseModel):
    game: str
    workspace: str
    agent: str = "claude"
    model: str = MODEL
    exit_code: int
    seconds: float
    audit: Audit = Audit()
    turns: int = 0
    tool_calls: int = 0
    compactions: int = 0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    score: int = 0
    win_levels: int = 0
    state: str = "UNKNOWN"
    actions_used: int = 0

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def child_env(api_key: str | None) -> dict[str, str]:
    """A clean environment for a spawned agent.

    The parent's CLAUDE_* variables identify *this* session; inheriting them
    would make the child a continuation of it rather than a session of its own,
    and would bill it accordingly.

    Without a broker, act.py runs inside the agent's own process tree and reads
    ARC_API_KEY from there — so the audit is what stands behind those runs, not
    the environment. With a broker the key never enters the agent's machine at
    all, and that is the configuration every published result used.

    Codex brings its own credential and there is no Anthropic key to hand it, so
    the model key is set only when there is one. Setting it to None instead put
    a null in the environment and every session died before starting.

    The database connection string goes too. It is how the harness keeps its
    record, and that record includes earlier runs of this very game — an agent
    that read it would be reading someone else's solution. Nothing the agent
    does needs it.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CLAUDE_CODE_", "CLAUDECODE", "CLAUDE_"))
    }
    env.pop("ANT_API_KEY", None)
    env.pop("POSTGRES_DSN", None)
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    # Optional telemetry, whose hosts a fenced sandbox refuses anyway. Asking
    # for it off is cheaper than letting every session retry a blocked address.
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    return env


def make_workspace(root: Path, game: str, broker: str | None) -> Path:
    """A workspace holds the prompt and a way to act, and nothing else.

    With a broker there is no actuator here at all — no key, no session
    cookies — only a client that forwards to it. `act` reads the same either
    way, so the prompt does not change.
    """
    ws = root / game
    ws.mkdir(parents=True)
    # The brief says what this environment is; PROMPT.md says how to play and
    # names no environment. A new benchmark means a new brief and actuator —
    # the prompt travels unchanged.
    (ws / "CLAUDE.md").write_text(
        (REPO / "ARC.md").read_text() + "\n" + (REPO / "PROMPT.md").read_text()
    )
    shim = ws / "act"
    if broker:
        # The shim carries which game this is and where the broker lives, so
        # `./act` works from any shell in any directory. Leaving that to the
        # environment meant it worked for the launcher and failed for the agent,
        # which quietly wrote its own wrapper to supply what was missing.
        shutil.copy(REPO / "rig" / "client.py", ws / "client.py")
        shim.write_text(
            "#!/bin/sh\n"
            f'export ARCSEC_BROKER="{broker}" ARCSEC_GAME="{game}"\n'
            f'exec python3 "{ws / "client.py"}" "$@"\n'
        )
    else:
        shim.write_text(f'#!/bin/sh\nexec uv run --project "{REPO}" python "{REPO}/act.py" "$@"\n')
    shim.chmod(0o755)
    return ws


async def run_act(ws: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(REPO / "act.py"),
        *args,
        cwd=ws,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    text = out.decode()
    if proc.returncode != 0:
        raise RuntimeError(f"act {' '.join(args)} failed in {ws}:\n{text}")
    return text


async def run_client(ws: Path, game: str, broker: str, *args: str) -> str:
    """Drive the workspace's own client, the way the agent will."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(ws / "client.py"),
        *args,
        cwd=ws,
        env=os.environ | {"ARCSEC_BROKER": broker, "ARCSEC_GAME": game},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    text = out.decode()
    if proc.returncode != 0:
        raise RuntimeError(f"client {' '.join(args)} failed in {ws}:\n{text}")
    return text


def tell_broker_done(broker: str, game: str) -> None:
    """Say the session has ended, so the batch's card can close on time.

    Only the launcher knows: a session can stop with most of its budget left,
    which the broker cannot distinguish from a long think. ARC reaps an idle
    card in fifteen minutes and a closed card is the only source of its own
    scoring, so this is the difference between having those numbers and not.
    """
    body = json.dumps({"game": game}).encode()
    request = Request(  # noqa: S310
        f"{broker.rstrip('/')}/done",
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ.get('ARCSEC_TOKEN', '')}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:  # noqa: S310
            answer = json.load(response)
    except OSError as exc:
        print(f"[{game}] could not tell the broker it finished: {exc}", flush=True)
        return
    if answer.get("closed"):
        score = answer.get("official", {}).get("score")
        print(f"[{game}] last one home — scorecard closed, score {score}", flush=True)


async def play(
    game: str,
    root: Path,
    args: argparse.Namespace,
    env: dict[str, str],
    card: Scorecard | None,
    limit: asyncio.Semaphore,
) -> Report:
    async with limit:
        # Claim the row before anything plays. The broker starts writing actions
        # during init, and those rows point at this one.
        if args.record:
            await asyncio.to_thread(
                db.open_game, args.record, game, socket.gethostname(), args.max_actions
            )
        if args.resume and not args.again:
            # The workspace is the memory: a fresh agent reads the log and the
            # notes the dead one left and carries on. Nothing to initialise.
            ws = root / game
            print(f"[{game}] resuming — playing", flush=True)
        elif args.again:
            # The card that held this game is gone, so the game itself has to
            # start over. Only the game: the notes, the scripts and the last
            # attempt's log stay where they are.
            ws = root / game
            card.save(ws)
            init = ["init", game, "--max-actions", str(args.max_actions), "--again"]
            await run_act(ws, *init)
            print(f"[{game}] playing again with the last attempt's notes", flush=True)
        else:
            ws = make_workspace(root, game, args.broker)
            init = ["init", game, "--max-actions", str(args.max_actions)]
            if args.broker:
                # The broker holds the key and the card; it initialises the game
                # and the client mirrors the opening board back here.
                await run_client(ws, game, args.broker, *init)
            else:
                card.save(ws)  # every game plays onto the one scorecard
                await run_act(ws, *init)
            print(f"[{game}] initialised — playing", flush=True)

        # The workspace is the evidence and the machine holding it may not
        # survive the game, so from here on it is mirrored to the database as
        # it grows rather than collected at the end.
        tracker = asyncio.create_task(db.track(args.record, game, ws)) if args.record else None

        started = time.monotonic()
        agent = AGENTS[args.agent]
        proc = await asyncio.create_subprocess_exec(
            *agent.argv(RESUME_TASK if args.resume else TASK, args.model, ws),
            cwd=ws,
            env=env,
            stdin=asyncio.subprocess.DEVNULL,  # codex reads stdin if it is a pipe
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=STREAM_LIMIT,
        )
        report = Report(
            game=game,
            workspace=str(ws),
            agent=args.agent,
            model=args.model,
            exit_code=0,
            seconds=0.0,
        )
        # Line-buffered: a run that is killed rather than finished still leaves a
        # readable transcript, and the file can be watched while it plays.
        with (ws / "agent_stream.jsonl").open("w", buffering=1) as stream:
            async for raw in proc.stdout:
                line = raw.decode(errors="replace")
                stream.write(line)
                absorb(agent, report, line)
        stderr = (await proc.stderr.read()).decode(errors="replace")
        await proc.wait()

        report.exit_code = proc.returncode
        report.seconds = time.monotonic() - started
        if stderr.strip():
            (ws / "agent_stderr.log").write_text(stderr)

        # With a broker the game's state lives there, not here, so it comes back
        # from the database the broker has been writing to all along.
        state = (
            db.game_state(args.record, game)
            if args.broker
            else json.loads((ws / "state.json").read_text())
        )
        report.score = state["score"]
        report.win_levels = state["win_levels"]
        report.state = state["state"]
        report.actions_used = state["actions_used"]
        report.audit = audit_session(ws / "agent_stream.jsonl", agent)
        (ws / "report.json").write_text(report.model_dump_json(indent=2))
        if tracker:
            tracker.cancel()
            # Awaiting the cancelled task surfaces a mirror that died hours ago
            # instead of letting the run finish believing it was recorded.
            with suppress(asyncio.CancelledError):
                await tracker
            await asyncio.to_thread(db.finish_game, args.record, game, ws, report.model_dump())
        if args.broker:
            await asyncio.to_thread(tell_broker_done, args.broker, game)

        flag = "" if report.ok else f" EXIT {report.exit_code}"
        print(
            f"[{game}] {report.state} {report.score}/{report.win_levels} levels, "
            f"{report.actions_used} actions, {report.turns} turns, "
            f"${report.cost_usd:.2f}, {report.seconds / 60:.1f} min{flag}",
            flush=True,
        )
        if not report.ok:
            print(f"[{game}] stderr tail: {stderr.strip()[-500:]}", flush=True)
        if not report.audit.clean:
            print(f"[{game}] AUDIT FAILED — this run is not evidence:", flush=True)
            for label, hits in report.audit.findings.items():
                print(f"[{game}]   {label}: {hits[0]}", flush=True)
        return report


def absorb(agent, report: Report, line: str) -> None:
    """Fold one streamed event into the run's telemetry.

    The two CLIs emit different shapes, and non-JSON chatter besides, so which
    fields mean what is the agent adapter's problem rather than this one's.
    """
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return
    agent.absorb(report, event)


def summarise(reports: list[Report], root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps([r.model_dump() for r in reports], indent=2))
    if not reports:
        print("\nno game produced a report — every one of them failed to run")
        return
    width = max(len(r.game) for r in reports)
    print(f"\n{'game'.ljust(width)}  levels  actions  turns   cost   minutes  state")
    for r in sorted(reports, key=lambda r: r.game):
        mark = "" if r.audit.clean else "  AUDIT FAILED"
        print(
            f"{r.game.ljust(width)}  {r.score:>2}/{r.win_levels:<3}  {r.actions_used:>7}  "
            f"{r.turns:>5}  ${r.cost_usd:>5.2f}  {r.seconds / 60:>7.1f}  {r.state}{mark}"
        )
    total_cost = sum(r.cost_usd for r in reports)
    tokens = sum(r.input_tokens + r.output_tokens for r in reports)
    cached = sum(r.cache_read_tokens for r in reports)
    boards = sum(r.audit.boards_in_context for r in reports)
    print(
        f"\n{len(reports)} games, {sum(r.score for r in reports)} levels, "
        f"${total_cost:.2f}, {tokens:,} tokens (+{cached:,} cached), "
        f"artifacts in {root}"
    )
    dirty = [r.game for r in reports if not r.audit.clean]
    verdict = f"AUDIT FAILED: {', '.join(dirty)}" if dirty else "audit clean"
    print(f"{verdict}; {boards} boards read into context rather than parsed")


def unfinished(root: Path) -> tuple[list[str], Scorecard | None]:
    """Games in a launch directory that still have a game left to play.

    Their scorecard comes back with them: it is recorded in each workspace's
    state, and the games have to keep playing onto the card they started on.
    """
    games, card = [], None
    for ws in sorted(p for p in root.iterdir() if p.is_dir()):
        state_file = ws / "state.json"
        if not state_file.exists():
            # A brokered workspace keeps no state here — the broker owns the
            # game. Include it and let the session learn where it stands from
            # `./act status`; resuming a game that is already won costs the
            # agent one look to notice and stop.
            if (ws / "act").exists():
                games.append(ws.name)
            continue
        state = json.loads(state_file.read_text())
        if state["state"] == "WIN" or state["actions_used"] >= state["max_actions"]:
            continue
        games.append(ws.name)
        if state.get("scorecard_id") and card is None:
            card = Scorecard(card_id=state["scorecard_id"], cookies=state.get("cookies", {}))
    return games, card


async def main() -> int:
    parser = argparse.ArgumentParser(prog="run", description=__doc__.splitlines()[0])
    parser.add_argument("games", nargs="*", help="game ids, e.g. ft09-0d8bbf25")
    parser.add_argument(
        "--resume",
        metavar="LAUNCH_DIR",
        help="carry on every unfinished game in a previous launch directory",
    )
    parser.add_argument(
        "--max-actions", type=int, default=DEFAULT_BUDGET, help="action budget per game"
    )
    parser.add_argument(
        "--agent",
        default="claude",
        choices=sorted(AGENTS),
        help="which coding agent plays: claude (Claude Code) or codex",
    )
    parser.add_argument(
        "--model",
        help="model for the agent sessions (default: the agent's own)",
    )
    parser.add_argument("-c", "--concurrency", type=int, default=5, help="games at once")
    parser.add_argument(
        "--broker",
        metavar="URL",
        help="play through a broker holding the key, instead of an actuator on this disk",
    )
    parser.add_argument(
        "--record",
        metavar="RUN",
        help="mirror this launch to Postgres under this name, and name its directory so",
    )
    args = parser.parse_args()

    load_dotenv(REPO / ".env")
    args.model = args.model or AGENTS[args.agent].model
    api_key = os.environ.get("ANT_API_KEY")
    if args.agent == "claude" and not api_key:
        raise SystemExit(
            "run: ANT_API_KEY is not set — put it in .env or the environment. "
            "It is passed to each agent session as ANTHROPIC_API_KEY."
        )
    if args.agent == "codex" and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "run: OPENAI_API_KEY is not set. Codex also needs it stored once with "
            "`printenv OPENAI_API_KEY | codex login --with-api-key`."
        )

    args.again = False
    if args.resume:
        root = Path(args.resume)
        args.games, card = unfinished(root)
        if not args.games:
            raise SystemExit(f"run: nothing left to play in {root}")
        # ARC drops a card once it is closed and reaps it after fifteen minutes
        # idle, killing its sessions. Replaying onto one is the `game not found`
        # that wasted a whole resumed batch, so check before trusting it.
        if card and not card.alive():
            card = Scorecard.open(tags=["arc-code"])
            args.again = True
            print(f"the old scorecard is gone — playing again on {card.card_id}")
        print(f"resuming {len(args.games)} games in {root}: {', '.join(args.games)}")
    else:
        # With a broker the card belongs to it, along with the key needed to
        # open one. Asking for a card here would fail, and should.
        card = Scorecard.open(tags=["arc-code"]) if not args.broker else None
        if card:
            print(f"scorecard {card.card_id}")
        root = RUNS / (args.record or datetime.now(UTC).strftime("%Y%m%d-%H%M%S"))
    if args.record:
        db.open_run(args.record, "online", args.model, args.max_actions)
    env = child_env(api_key)
    limit = asyncio.Semaphore(args.concurrency)
    # One game blowing up must not discard the other fourteen. Failures are
    # reported and still fail the run; they just do not take the results with
    # them, which matters when a batch has been playing for hours.
    results = await asyncio.gather(
        *(play(game, root, args, env, card, limit) for game in args.games),
        return_exceptions=True,
    )
    reports = [r for r in results if isinstance(r, Report)]
    for game, result in zip(args.games, results, strict=True):
        if not isinstance(result, Report):
            print(f"[{game}] FAILED TO RUN: {result}", flush=True)

    summarise(reports, root)
    if card:
        # Closing is the only way to get ARC's own scoring, and only while the
        # session still holds the card — leave it open and the numbers are lost.
        official = card.close()
        (root / "scorecard.json").write_text(json.dumps(official, indent=2))
        if args.record:
            db.record_official(args.record, args.games, card.card_id, official)
        print(
            f"official score {official.get('score')} — "
            f"{official.get('total_levels_completed')}/{official.get('total_levels')} levels, "
            f"{official.get('total_actions')} actions"
        )
        print(f"scorecard: https://arcprize.org/scorecards/{card.card_id}")
    if args.record:
        db.close_run(args.record)
        print(f"recorded as {args.record} — db.py show {args.record}")
    lost = len(args.games) - len(reports)
    return 0 if not lost and all(r.ok and r.audit.clean for r in reports) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
