#!/usr/bin/env python3
"""Play games in the cloud, one sandbox each, on a machine that stays up.

A hard game runs for hours; laptops sleep and dev containers restart. So each
game gets its own sandbox and plays there, and this script is only a remote
control — start it, walk away, come back from anywhere and look:

    uv run --with e2b cloud.py build                    # once, or after a change
    uv run --with e2b cloud.py start ls20-9607627b --broker
    uv run --with e2b cloud.py watch <run>
    uv run db.py pull <run>                             # the artifacts, later

Nothing here is stateful. Sandboxes are tagged with the run they belong to, so
they can be found again with no bookkeeping on this side — which is the point,
because this side is the part that keeps dying. The results do not come back
through here at all: each game writes itself to Postgres as it plays, so
nothing depends on a sandbox surviving long enough to be asked.
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_hex
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Run directly as well as imported, so the repo root has to be on the path
# before `act` is imported. rig/ is not a package: a sandbox overwrites these
# files between the image build and launch, and an installed copy would
# shadow the fresh one.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db
from agents import AGENTS
from dotenv import dotenv_values
from e2b import Sandbox, Template
from e2b.sandbox.sandbox_api import SandboxQuery

import act

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = "arc-code"
WORK = "/arc-code"  # where the template puts the harness
HOUR = 3600
# Everything the harness needs, and nothing else. The venv is baked at build
# time so a sandbox is ready to play the moment it starts.
PAYLOAD = [
    "act.py",
    "run.py",
    "PROMPT.md",
    "ARC.md",
    "rig/db.py",
    "rig/agents.py",
    "rig/audit.py",
    "rig/broker.py",
    "rig/client.py",
    "pyproject.toml",
    "uv.lock",
]
BROKER_PORT = 8000
# The model API each agent has to reach, and the only host it has in common with
# a human's machine.
MODEL_HOST = {"claude": "api.anthropic.com", "codex": "api.openai.com"}


def host_of(url: str) -> str:
    """The hostname in a URL or a Postgres DSN — an allow list entry is a host,
    and a missing one would silently widen the fence."""
    host = urlparse(url).hostname
    if not host:
        raise SystemExit(f"cloud: no host to allow in {url[:40]!r}")
    return host


def fence(*allow: str) -> dict:
    """Deny all egress, then allow these hosts and nothing else.

    Much has been written about the public ARC-AGI-3 games, and some of it —
    the games' own source files, other harnesses' published traces — amounts to
    a solution. An agent that can fetch a page can fetch an answer, and then a
    score means nothing. So the sandbox is fenced by E2B — beneath the agent,
    beneath its CLI, and identically for both, which a CLI's own sandbox flag
    cannot manage: Claude Code takes a domain allow list, Codex takes only
    network on or off.

    Verified from inside a fenced sandbox: example.com, github.com,
    raw.githubusercontent.com, pypi.org, google.com and a bare `https://1.1.1.1`
    are all refused at the handshake, over IPv4 and IPv6 alike, while the model
    API and the broker answer. Matching is by SNI and Host header and is exact,
    so allowing `api.anthropic.com` does not allow `console.anthropic.com`.

    One channel stays open and is worth stating plainly: names still resolve,
    because an allow list written in domains needs a resolver. DNS is therefore
    a covert channel, and too narrow to carry a walkthrough — the audit watches
    for the tools that would use it.
    """
    return {"deny_out": lambda ctx: [ctx.all_traffic], "allow_out": list(allow)}


def secrets(agent: str = "claude") -> dict[str, str]:
    """Keys from .env and the environment, .env winning.

    Which model key is required depends on who is playing; the game key and the
    database are needed either way.
    """
    found = {**os.environ, **{k: v for k, v in dotenv_values(REPO / ".env").items() if v}}
    need = {"claude": "ANT_API_KEY", "codex": "OPENAI_API_KEY"}[agent]
    missing = [k for k in ("E2B_API_KEY", need, "POSTGRES_DSN") if not found.get(k)]
    if missing:
        raise SystemExit(f"cloud: {', '.join(missing)} not set — put them in .env")
    os.environ["E2B_API_KEY"] = found["E2B_API_KEY"]
    return found


def build(args: argparse.Namespace) -> None:
    """Bake the image: node, the Claude CLI, uv, the harness, its venv."""
    template = (
        # Paths in `.copy` are resolved inside this context, which otherwise
        # defaults to the calling file's directory — rig/, not the repo root.
        Template(file_context_path=REPO)
        .from_node_image("22")  # the CLI warns EBADENGINE on node 20
        .set_user("root")
        .apt_install(["curl", "git", "ca-certificates"])
        .npm_install("@anthropic-ai/claude-code", g=True)
        # both CLIs, so a batch can be played by either without a rebuild
        .npm_install("@openai/codex", g=True)
        # into /usr/local/bin so uv is on PATH for every user, not just root
        .run_cmd("curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh")
        .set_envs({"PYTHONUNBUFFERED": "1"})
        .make_dir(WORK)
        .copy(["pyproject.toml", "uv.lock"], f"{WORK}/")
        .set_workdir(WORK)
        .run_cmd("uv sync --frozen")
    )
    info = Template.build(
        template,
        alias=TEMPLATE,
        cpu_count=args.cpu,
        memory_mb=args.memory,
        on_build_logs=lambda entry: print(" ", str(entry)[:120]),
    )
    print(f"built {info.alias} ({args.cpu} cpu, {args.memory} MB)")


def raise_broker(run: str, keys: dict[str, str], hours: int, games: list[str]) -> tuple[str, str]:
    """One sandbox per batch holding the key, the sessions and the log.

    It is the only machine with ARC_API_KEY, and after the fence it is the only
    one that can reach the game API at all. The agents get its address and a
    token, which they must have in order to play — the token keeps strangers
    off a public URL, it is not a restraint on them.
    """
    token = token_hex(16)
    sandbox = Sandbox.create(
        template=TEMPLATE,
        timeout=hours * HOUR,
        # It plays the games and writes the record, and has no other business.
        network=fence(host_of(act.BASE_URL), host_of(keys["POSTGRES_DSN"])),
        # The token travels in the tag so any machine can find the broker again
        # and close its card. It keeps strangers off a public URL; it is not a
        # secret from the operator, and this side deliberately keeps no state of its own.
        metadata={"run": run, "role": "broker", "token": token},
        envs={
            "ARC_API_KEY": keys["ARC_API_KEY"],
            "POSTGRES_DSN": keys["POSTGRES_DSN"],
            "ARCSEC_TOKEN": token,
            "ARCSEC_RUN": run,
            "ARCSEC_WORK": "/broker",
            # so it knows when the last game is home and the card must close
            "ARCSEC_GAMES": ",".join(games),
            # how long the card may sit idle before the watchdog closes it,
            # only when asked for — the broker has its own default.
            **(
                {"ARCSEC_IDLE_CLOSE": os.environ["ARCSEC_IDLE_CLOSE"]}
                if os.environ.get("ARCSEC_IDLE_CLOSE")
                else {}
            ),
        },
    )
    for name in PAYLOAD:
        sandbox.files.write(f"{WORK}/{name}", (REPO / name).read_text())
    sandbox.commands.run(
        f"cd {WORK} && uv run rig/broker.py > {WORK}/broker.log 2>&1",
        background=True,
        timeout=0,
    )
    url = f"https://{sandbox.get_host(BROKER_PORT)}"
    for _ in range(30):
        try:
            with urlopen(f"{url}/health", timeout=10):  # noqa: S310
                break
        except OSError:
            time.sleep(2)
    else:
        raise SystemExit(f"cloud: broker never answered at {url}")
    print(f"broker {sandbox.sandbox_id} at {url}")
    return url, token


def start(args: argparse.Namespace) -> None:
    keys = secrets(args.agent)
    model = AGENTS[args.agent].model
    run = args.run or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    # Opened here rather than by the sandboxes so that `watch` has something to
    # read from the moment this returns, and so fifteen of them do not race.
    db.open_run(run, "online", model, args.max_actions)
    envs = {"POSTGRES_DSN": keys["POSTGRES_DSN"]}
    # Belongs to the batch, not to a game, so it is set once here and read by
    # the agent adapter inside the sandbox.
    if args.effort:
        envs["ARCSEC_EFFORT"] = args.effort
    if args.agent == "codex":
        envs["OPENAI_API_KEY"] = keys["OPENAI_API_KEY"]
    else:
        envs["ANT_API_KEY"] = keys["ANT_API_KEY"]
    broker = ""
    if args.broker:
        broker, token = raise_broker(run, keys, args.hours, args.games)
        envs |= {"ARCSEC_BROKER": broker, "ARCSEC_TOKEN": token}
    else:
        # Without a broker the actuator runs beside the agent, which means the
        # key does too, and the game API has to be reachable from here.
        envs["ARC_API_KEY"] = keys.get("ARC_API_KEY", "")
    # A game sandbox needs its model, the record, and — through the broker — the
    # game. With a broker it cannot reach the game API even in principle, so the
    # boundary no longer rests on withholding a key.
    allow = [MODEL_HOST[args.agent], host_of(keys["POSTGRES_DSN"])]
    allow += [host_of(broker)] if broker else [host_of(act.BASE_URL)]
    for game in args.games:
        sandbox = Sandbox.create(
            template=TEMPLATE,
            timeout=args.hours * HOUR,
            metadata={"run": run, "game": game},
            envs=envs,
            network=fence(*allow),
        )
        # The template bakes a copy of the harness, but it is a cache of the
        # environment — node, the CLI, uv, the venv — not of the code. Pushing
        # the working tree over it means a run always plays the prompt and the
        # actuator that are in the repository now, rather than whatever was
        # current when the image was last built.
        for name in PAYLOAD:
            sandbox.files.write(f"{WORK}/{name}", (REPO / name).read_text())
        if args.agent == "codex":
            # Codex ignores OPENAI_API_KEY and reads a stored credential, so it
            # has to be told once per sandbox before anything will authenticate.
            sandbox.commands.run(
                "printenv OPENAI_API_KEY | codex login --with-api-key", envs=envs, timeout=120
            )
        sandbox.commands.run(
            f"cd {WORK} && uv run run.py {game} -c 1 --max-actions {args.max_actions}"
            f" --agent {args.agent} --record {run}"
            f"{f' --broker {broker}' if broker else ''}"
            f" > {WORK}/console.log 2>&1",
            background=True,
            timeout=0,
        )
        print(f"[{game}] {sandbox.sandbox_id}")
    print(f"\nrun {run} — {len(args.games)} playing\n  watch:  cloud.py watch {run}")


def tagged(run: str) -> list[tuple[dict, Sandbox]]:
    """Every sandbox belonging to a run, found by its tag rather than by notes
    kept on this machine."""
    pages = Sandbox.list(SandboxQuery(metadata={"run": run}))
    found = []
    while True:
        for info in pages.next_items():
            found.append((info.metadata or {}, Sandbox.connect(info.sandbox_id)))
        if not pages.has_next:
            return found


def sandboxes(run: str) -> list[tuple[str, Sandbox]]:
    """The game sandboxes of a run, by game."""
    playing = [(tag.get("game", "?"), sb) for tag, sb in tagged(run) if tag.get("role") != "broker"]
    return sorted(playing, key=lambda pair: pair[0])


def broker_of(run: str) -> tuple[Sandbox, str, str] | None:
    """A run's broker, its address and its token — recovered from the tag."""
    for tag, sandbox in tagged(run):
        if tag.get("role") == "broker":
            return sandbox, f"https://{sandbox.get_host(BROKER_PORT)}", tag.get("token", "")
    return None


def close_card(run: str) -> None:
    """Ask a run's broker to close its scorecard, which is the only way to get
    ARC's own scoring — and only possible while the card is still open."""
    found = broker_of(run)
    if not found:
        return
    _, url, token = found
    request = Request(  # noqa: S310
        f"{url}/close",
        data=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310
            body = json.load(response)
    except OSError as exc:
        print(f"could not close the scorecard: {exc}")
        return
    if body.get("closed"):
        # A card closed by the broker's watchdog, or by the last game reporting
        # in, is already scored and recorded — closing again is a no-op that
        # returns no scoring, which is success rather than something to trip on.
        official = body.get("official")
        if official:
            print(
                f"official score {official.get('score')} — "
                f"{official.get('total_levels_completed')}/{official.get('total_levels')} levels"
            )
        else:
            print(f"scorecard was already closed ({body.get('why', 'earlier')})")
        print(f"scorecard: https://arcprize.org/scorecards/{body['card_id']}")


def watch(args: argparse.Namespace) -> None:
    """Progress, read from the database rather than from the sandboxes.

    The games report as they play, so this works whether they are still running
    or died hours ago — which is the point, since a finished sandbox is gone and
    a wedged one answers questions it should not be trusted on.
    """
    secrets()
    while True:
        rows = db.sql(
            "select game, state, score, win_levels, actions_used, max_actions, finished_at,"
            " extract(epoch from now() - updated_at)::int as stale"
            " from games where run = $1 order by game",
            args.run,
        )
        if not rows:
            raise SystemExit(f"cloud: no run {args.run} — has it started?")
        alive = len(sandboxes(args.run))
        print(f"\n{datetime.now().strftime('%H:%M:%S')}  run {args.run}  {alive} sandboxes up")
        for r in rows:
            # A row nobody has touched for minutes is the sign of a dead
            # sandbox, and the only way to tell one from a game that is thinking.
            quiet = f"  last seen {r['stale'] // 60}m ago" if r["stale"] > 180 else ""
            print(
                f"  {r['game']:<16} {r['score']}/{r['win_levels']} levels"
                f"  {r['actions_used']:>4} actions  {r['state']}{quiet}"
            )
        done = sum(1 for r in rows if r["finished_at"])
        if done == len(rows):
            print(f"\nall {done} finished — db.py pull {args.run}")
            close_card(args.run)
            return
        if not args.follow:
            return
        time.sleep(args.every)


def adopt(args: argparse.Namespace) -> None:
    """Start recording a batch that is already playing.

    For a run launched before it knew about the database, or one whose recorder
    died with the process that started it. The sandbox gets the current db.py
    and a mirror loop of its own, so the games carry on untouched and start
    reporting from wherever they have got to.

    It recovers everything the workspace holds, which is everything except
    ARC's own scoring: that arrives from `scorecard/close` after the game has
    ended, and the launcher — which knows nothing about this database — writes
    it beside the workspace rather than in it. Runs started with `--record`
    keep it.
    """
    keys = secrets()
    model = AGENTS[args.agent].model
    db.open_run(args.run, "online", model, args.max_actions)
    for game, sandbox in sandboxes(args.run):
        ws = sandbox.commands.run(f"ls -d {WORK}/runs/*/{game}", timeout=30).stdout.strip()
        # Adopting twice must replace the recorder, not add a second one. The
        # backslash keeps the pattern from matching the shell running it: the
        # shell's own command line carries `db\.py`, which `\.` does not match.
        sandbox.commands.run('pkill -f "db\\.py mirror" || true', timeout=30)
        sandbox.files.write(f"{WORK}/rig/db.py", (REPO / "rig" / "db.py").read_text())
        db.open_game(args.run, game, sandbox.sandbox_id, args.max_actions)
        sandbox.commands.run(
            f"cd {WORK} && uv run rig/db.py mirror {args.run} {game} {ws}"
            f" >> {WORK}/mirror.log 2>&1",
            envs={"POSTGRES_DSN": keys["POSTGRES_DSN"]},
            background=True,
            timeout=0,
        )
        print(f"  {game}: mirroring {ws}")
    print(f"\nrun {args.run} adopted — cloud.py watch {args.run}")


def logs(args: argparse.Namespace) -> None:
    """The console of each sandbox — for the failures that happen before a game
    exists to report on itself. Everything after that is in the database."""
    secrets()
    for game, sandbox in sandboxes(args.run):
        tail = sandbox.commands.run(f"tail -n {args.lines} {WORK}/console.log", timeout=30).stdout
        print(f"\n=== {game} ===\n{tail.rstrip()}")


def stop(args: argparse.Namespace) -> None:
    secrets()
    close_card(args.run)  # a killed broker takes ARC's scoring with it
    for game, sandbox in tagged(args.run):
        game = game.get("game", "broker")
        sandbox.kill()
        print(f"  {game}: stopped")


def main() -> int:
    parser = argparse.ArgumentParser(prog="cloud", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="bake the sandbox image")
    p.add_argument("--cpu", type=int, default=2)
    p.add_argument("--memory", type=int, default=4096)
    p.set_defaults(func=build)

    p = sub.add_parser("start", help="play games, one sandbox each")
    p.add_argument("games", nargs="+")
    p.add_argument(
        "--agent", default="claude", choices=sorted(AGENTS), help="who plays: claude or codex"
    )
    p.add_argument(
        "--broker",
        action="store_true",
        help="hold the key in a broker sandbox instead of beside every agent",
    )
    p.add_argument("--max-actions", type=int, default=2500)
    p.add_argument(
        "--effort",
        choices=["minimal", "low", "medium", "high", "xhigh", "max", "ultra"],
        help="how hard the agent thinks per turn; unset leaves each CLI's own"
        " default (high for both). Not every level exists on every agent",
    )
    p.add_argument("--hours", type=int, default=6, help="sandbox lifetime")
    p.add_argument("--run", help="name this run (default: a timestamp)")
    p.set_defaults(func=start)

    p = sub.add_parser("watch", help="how the games are doing")
    p.add_argument("run")
    p.add_argument("-f", "--follow", action="store_true")
    p.add_argument("--every", type=int, default=60)
    p.set_defaults(func=watch)

    p = sub.add_parser("adopt", help="start recording a batch already playing")
    p.add_argument("run")
    p.add_argument("--agent", default="claude", choices=sorted(AGENTS))
    p.add_argument("--max-actions", type=int, default=2500)
    p.set_defaults(func=adopt)

    p = sub.add_parser("logs", help="each sandbox's console, for failures to start")
    p.add_argument("run")
    p.add_argument("-n", "--lines", type=int, default=20)
    p.set_defaults(func=logs)

    p = sub.add_parser("stop", help="kill a run's sandboxes")
    p.add_argument("run")
    p.set_defaults(func=stop)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
