#!/usr/bin/env python3
"""The record. A run writes itself here while it is still playing.

A sandbox is somewhere to play, not somewhere to keep evidence: it can be
killed at any moment and it takes its disk with it. So a game reports as it
goes — its state on a timer, a row per action, and its whole workspace gzipped
whenever a file changes. Everything a run produced can then be read back from
anywhere, long after the machine that produced it is gone.

Postgres is reached over HTTPS rather than 5432, through Neon's SQL endpoint,
because that is the one protocol every environment this runs in allows.

    uv run db.py init                 # create the tables
    uv run db.py ls                   # runs, newest first
    uv run db.py show final15         # its games
    uv run db.py pull final15         # its artifacts, back onto this disk
    uv run db.py q "select ..."       # anything else
"""

import argparse
import asyncio
import gzip
import json
import os
import sys
import time
from base64 import b64decode, b64encode
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import dotenv_values

# Run directly as well as imported, so the repo root has to be on the path
# before `act` is imported. rig/ is not a package: a sandbox overwrites these
# files between the image build and launch, and an installed copy would
# shadow the fresh one.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from act import LOG, SEP, STATE  # the log parser below must track its writer

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
REPORT = "report.json"  # written by run.py once a game's session has ended
# The agents write and import their own modules, so their workspaces grow
# bytecode. It is not evidence, and it changes on every import, which would
# mean re-uploading it on every tick.
NOISE = {"__pycache__"}
RETRY_DELAYS = (1, 2, 4, 8, 16)
TIMEOUT = 180  # artifacts go up in the same request as everything else
MIRROR_EVERY = 60  # seconds; a killed sandbox loses at most this much

# The tables. `games` is the live row — upserted every mirror — while `actions`
# and `artifacts` only ever grow, so a run that dies mid-flight still leaves
# everything it had reached by the last tick.
DDL = [
    """create table if not exists runs (
        id           text primary key,
        started_at   timestamptz not null default now(),
        finished_at  timestamptz,
        mode         text not null,
        model        text not null,
        max_actions  int  not null,
        note         text
    )""",
    """create table if not exists games (
        run          text not null references runs(id) on delete cascade,
        game         text not null,
        host         text,
        started_at   timestamptz not null default now(),
        updated_at   timestamptz not null default now(),
        finished_at  timestamptz,
        state        text not null default 'STARTING',
        score        int  not null default 0,
        win_levels   int  not null default 0,
        level        int  not null default 1,
        attempt      int  not null default 1,
        actions_used int  not null default 0,
        max_actions  int,
        scorecard_id text,
        official     jsonb,
        exit_code    int,
        seconds      double precision,
        turns        int,
        tool_calls   int,
        compactions  int,
        cost_usd     double precision,
        input_tokens          bigint,
        output_tokens         bigint,
        cache_read_tokens     bigint,
        cache_creation_tokens bigint,
        audit        jsonb,
        primary key (run, game)
    )""",
    """create table if not exists actions (
        run     text not null,
        game    text not null,
        n       int  not null,
        level   int  not null,
        attempt int  not null,
        score   int  not null,
        action  text not null,
        x       int,
        y       int,
        plan    text,
        primary key (run, game, n),
        foreign key (run, game) references games (run, game) on delete cascade
    )""",
    """create table if not exists artifacts (
        run        text not null,
        game       text not null,
        name       text not null,
        bytes      int  not null,
        body       bytea not null,
        updated_at timestamptz not null default now(),
        primary key (run, game, name),
        foreign key (run, game) references games (run, game) on delete cascade
    )""",
    "create index if not exists actions_by_level on actions (run, game, level, n)",
    # Added once a second agent could play: without these, a row cannot say
    # whether Claude or Codex produced it, and the comparison is unreadable.
    "alter table games add column if not exists agent text",
    "alter table games add column if not exists model text",
    # A second verdict, from re-grading the stored stream under stricter patterns
    # than the ones the session was originally graded by. Kept beside the first
    # rather than over it, so the two can be compared.
    "alter table games add column if not exists reaudit jsonb",
]


# --------------------------------------------------------------------------- #
# Talking to Postgres over HTTPS
# --------------------------------------------------------------------------- #


@cache
def endpoint() -> tuple[str, dict[str, str]]:
    """Neon's SQL endpoint and the header that authenticates to it.

    The DSN is the credential — it travels in a header, not in the URL.
    """
    dsn = os.environ.get("POSTGRES_DSN") or dotenv_values(REPO / ".env").get("POSTGRES_DSN")
    if not dsn:
        raise SystemExit("db: POSTGRES_DSN is not set — put it in .env or the environment")
    return f"https://{urlparse(dsn).hostname}/sql", {"Neon-Connection-String": dsn}


def post(body: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    """POST to the SQL endpoint, retrying only what is worth retrying.

    Rate limits, a cold branch and network faults pass; a 4xx means the
    statement is wrong and asking again will not make it right.
    """
    url, auth = endpoint()
    for delay in (*RETRY_DELAYS, None):
        try:
            r = requests.post(url, headers={**auth, **(headers or {})}, json=body, timeout=TIMEOUT)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if delay is None:
                raise RuntimeError(f"db: unreachable after retries: {exc}") from exc
        else:
            if r.ok:
                return r.json()
            if r.status_code != 429 and r.status_code < 500:
                raise RuntimeError(f"db: HTTP {r.status_code}: {r.text[:400]}")
            if delay is None:
                raise RuntimeError(f"db: still HTTP {r.status_code} after retries: {r.text[:400]}")
        time.sleep(delay)
    raise AssertionError("unreachable")


def sql(query: str, *params: Any) -> list[dict[str, Any]]:
    """One statement, positional `$1`-style parameters, rows back as dicts."""
    return post({"query": query, "params": [encode(p) for p in params]})["rows"]


def batch(statements: list[tuple[str, tuple[Any, ...]]]) -> None:
    """Several statements in one transaction and one round trip."""
    if not statements:
        return
    post(
        {"queries": [{"query": q, "params": [encode(p) for p in ps]} for q, ps in statements]},
        {"Neon-Batch-Isolation-Level": "ReadCommitted"},
    )


def encode(value: Any) -> Any:
    """Parameters go over JSON, so anything that isn't JSON becomes text.

    ``bytes`` is base64 and the statement decodes it; dicts and lists are dumped
    for `jsonb`. Everything else Postgres can read from its own text form.
    """
    if isinstance(value, bytes):
        return b64encode(value).decode()
    if isinstance(value, dict | list):
        return json.dumps(value)
    return value


# --------------------------------------------------------------------------- #
# Writing a run down
# --------------------------------------------------------------------------- #


def open_run(run: str, mode: str, model: str, max_actions: int, note: str | None = None) -> None:
    """Claim the run's row. Harmless to call again: fifteen sandboxes playing
    one run all try, and the first one wins."""
    sql(
        "insert into runs (id, mode, model, max_actions, note) values ($1,$2,$3,$4,$5) "
        "on conflict (id) do nothing",
        run,
        mode,
        model,
        max_actions,
        note,
    )


def open_game(run: str, game: str, host: str | None, max_actions: int) -> None:
    sql(
        "insert into games (run, game, host, max_actions) values ($1,$2,$3,$4) "
        "on conflict (run, game) do update set host = excluded.host, updated_at = now()",
        run,
        game,
        host,
        max_actions,
    )


def close_run(run: str) -> None:
    sql("update runs set finished_at = now() where id = $1", run)


# What a game reports, by the name of the column it lands in. Every statement
# below is built from one of these lists rather than written out, so a column
# and its parameter cannot drift apart — the one bug this file has already had.
LIVE = (  # from state.json, on every tick
    "state",
    "score",
    "win_levels",
    "level",
    "attempt",
    "actions_used",
    "max_actions",
    "scorecard_id",
)
FINAL = (  # from report.json, once the session has ended
    "agent",
    "model",
    "exit_code",
    "seconds",
    "turns",
    "tool_calls",
    "compactions",
    "cost_usd",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
)
ACTION = ("n", "level", "attempt", "score", "action", "x", "y", "plan")  # from logs.txt


def slots(columns: tuple[str, ...], start: int = 3) -> str:
    """`$3,$4,$5` — the parameters a column list occupies, after run and game."""
    return ",".join(f"${i}" for i in range(start, start + len(columns)))


def assign(columns: tuple[str, ...], start: int = 3) -> str:
    """`state = $3, score = $4` — the same, as an update."""
    return ", ".join(f"{c} = ${i}" for i, c in enumerate(columns, start=start))


def mirror(run: str, game: str, ws: Path) -> None:
    """Push everything this workspace has reached: state, actions, files.

    Called on a timer while the game plays and once more when it stops. It
    reads only what is on disk, so it says the same thing whether the agent is
    alive, wedged or already gone.
    """
    push_state(run, game, ws)
    push_actions(run, game, ws / LOG)
    push_artifacts(run, game, ws)


def game_state(run: str, game: str) -> dict[str, Any]:
    """A game's state, read back from here rather than from a workspace.

    With a broker the state file is on the broker's disk, so the launcher asks
    the database — which the broker has been writing to after every action.
    """
    rows = sql(
        "select state, score, win_levels, actions_used from games where run = $1 and game = $2",
        run,
        game,
    )
    if not rows:
        raise RuntimeError(f"db: no row for {run}/{game} — did the broker record anything?")
    return rows[0]


def push_state(run: str, game: str, ws: Path) -> None:
    """What the game says about itself, from its own state file."""
    if not (ws / STATE).exists():
        return
    state = json.loads((ws / STATE).read_text())
    sql(
        f"update games set {assign(LIVE)}, updated_at = now() where run = $1 and game = $2",
        run,
        game,
        *(state.get(column) for column in LIVE),
    )


def push_actions(run: str, game: str, log: Path) -> None:
    """Append whatever the log has gained since the last look.

    For a caller that only has the file: it asks how far the record goes and
    parses the whole log to find the rest. Anyone holding just the new bytes
    should pass those to `push_slice` instead and skip both.
    """
    if not log.exists():
        return
    seen = sql(
        "select coalesce(max(n), -1) as high from actions where run = $1 and game = $2", run, game
    )[0]["high"]
    insert(run, game, [row for row in parse_log(log) if row["n"] > seen])


def push_slice(run: str, game: str, body: str) -> None:
    """Append the actions in a piece of log, without re-reading the whole thing.

    The broker knows exactly what act.py just wrote, so it costs nothing to say
    so — and re-parsing a log that reaches tens of megabytes after every single
    action would not stay cheap. Rows already present are left alone, so an
    overlapping slice is harmless.
    """
    insert(run, game, parse_log_text(body))


def insert(run: str, game: str, rows: list[dict[str, Any]]) -> None:
    batch(
        [
            (
                f"insert into actions (run, game, {', '.join(ACTION)})"
                f" values ($1,$2,{slots(ACTION)}) on conflict do nothing",
                (run, game, *(row[column] for column in ACTION)),
            )
            for row in rows
        ]
    )


def push_artifacts(run: str, game: str, ws: Path) -> None:
    """Upload every file whose size no longer matches what is stored.

    Size is a coarse test and a cheap one, and every file here is append-only
    or rewritten whole, so a change that keeps the length is not a thing that
    happens.
    """
    stored = {
        row["name"]: row["bytes"]
        for row in sql("select name, bytes from artifacts where run = $1 and game = $2", run, game)
    }
    # Read once and record the length of what was read, rather than stat-ing
    # again: the log and the agent's stream are being appended to as this runs,
    # and a size that disagrees with its body is a lie about what is stored.
    changed = []
    for path in sorted(f for f in ws.rglob("*") if f.is_file() and NOISE.isdisjoint(f.parts)):
        body = path.read_bytes()
        name = str(path.relative_to(ws))
        if stored.get(name) != len(body):
            changed.append((name, body))
    batch(
        [
            (
                "insert into artifacts (run, game, name, bytes, body)"
                " values ($1,$2,$3,$4,decode($5,'base64'))"
                " on conflict (run, game, name) do update set"
                " bytes = excluded.bytes, body = excluded.body, updated_at = now()",
                (run, game, name, len(body), gzip.compress(body)),
            )
            for name, body in changed
        ]
    )


def finish_game(run: str, game: str, ws: Path, report: dict[str, Any]) -> None:
    """The last word on a game: a final mirror, then what the session cost."""
    mirror(run, game, ws)
    sql(
        f"update games set {assign(FINAL)}, audit = ${len(FINAL) + 3},"
        " finished_at = now(), updated_at = now() where run = $1 and game = $2",
        run,
        game,
        *(report.get(column) for column in FINAL),
        report.get("audit"),
    )


def record_official(run: str, games: list[str], card_id: str, official: dict[str, Any]) -> None:
    """ARC's own scoring, against every game that played onto the card."""
    batch(
        [
            (
                "update games set scorecard_id = $3, official = $4 where run = $1 and game = $2",
                (run, game, card_id, official),
            )
            for game in games
        ]
    )


async def track(run: str, game: str, ws: Path, every: int = MIRROR_EVERY) -> None:
    """Mirror a workspace until cancelled. The blocking calls go to a thread so
    the launcher keeps draining the agent's stream while this talks to Neon."""
    while True:
        await asyncio.sleep(every)
        await asyncio.to_thread(mirror, run, game, ws)


def follow(args: argparse.Namespace) -> None:
    """Mirror a workspace until the game it holds is over.

    The same job `track` does inside the launcher, for a game already being
    played by a process that knows nothing about this database. It stops on
    `report.json`, which the launcher writes once and only once the session has
    ended — so an adopted run finishes as completely as a recorded one.
    """
    ws = Path(args.workspace)
    while True:
        mirror(args.run, args.game, ws)
        if (ws / REPORT).exists():
            finish_game(args.run, args.game, ws, json.loads((ws / REPORT).read_text()))
            print(f"{args.game}: finished — {args.run}")
            return
        time.sleep(args.every)


# --------------------------------------------------------------------------- #
# Reading a log back as rows
# --------------------------------------------------------------------------- #


def parse_log(log: Path) -> list[dict[str, Any]]:
    """Every action the log records, as a row.

    ``logs.txt`` is the ground truth for what was played — state.json keeps only
    the shape of it — and its headers already carry the level, the attempt and
    the score the action produced, which is exactly what scoring needs.
    """
    return parse_log_text(log.read_text(errors="replace"))


def parse_log_text(body: str) -> list[dict[str, Any]]:
    """The same, for a log that is in hand rather than on disk.

    Reads both the current block format and the earlier one the published
    bundle's runs were logged in.
    """
    rows = []
    for block in body.split(SEP):
        head = block.strip().splitlines()
        if not head:
            continue
        if head[0].startswith("action "):
            rows.append(parse_block(block, head[0]))
        elif head[0].startswith("Action "):
            rows.append(parse_v1_block(block, head[0]))
    return rows


def parse_block(block: str, header: str) -> dict[str, Any]:
    """`action N | level L attempt A | score S | <played> | step i/k`."""
    parts = [p.strip() for p in header.split(" | ")]
    level_attempt = parts[1].split()
    played = parts[3].split()
    coords = dict(kv.split("=") for kv in played[1:])
    plan = block.partition("plan: ")[2].partition("\n\n[board]")[0]
    return {
        "n": int(parts[0].split()[1]),
        "level": int(level_attempt[1]),
        "attempt": int(level_attempt[3]),
        "score": int(parts[2].split()[1]),
        "action": "INITIAL" if played[0] == "start" else played[0],
        "x": int(coords["x"]) if "x" in coords else None,
        "y": int(coords["y"]) if "y" in coords else None,
        "plan": plan.strip() or None,
    }


def parse_v1_block(block: str, header: str) -> dict[str, Any]:
    """`Action N | Level L | Attempt A | Score: S` with a Tool Call line."""
    head = block.strip().splitlines()
    call = next((line for line in head if line.startswith("Tool Call: ")), "")
    name, _, rest = call.removeprefix("Tool Call: ").partition("(")
    data = json.loads(rest.rstrip(")") or "{}") if rest else {}
    plan = block.partition("[PLAN]\n")[2].partition("\n\nTool Call:")[0]
    return {
        "n": field(header, "Action"),
        "level": field(header, "Level"),
        "attempt": field(header, "Attempt"),
        "score": field(header, "Score"),
        "action": name or "INITIAL",
        "x": data.get("x"),
        "y": data.get("y"),
        "plan": plan.strip() or None,
    }


def field(header: str, name: str) -> int:
    """One `Name 3` or `Name: 3` field out of a log header line."""
    for part in header.split(" | "):
        label, _, value = part.replace(":", "").partition(" ")
        if label == name:
            return int(value)
    raise ValueError(f"db: no {name} in log header {header!r}")


# --------------------------------------------------------------------------- #
# Looking at it
# --------------------------------------------------------------------------- #


def init(args: argparse.Namespace) -> None:
    batch([(statement, ()) for statement in DDL])
    print(f"{len(DDL)} statements applied — runs, games, actions, artifacts")


def ls(args: argparse.Namespace) -> None:
    rows = sql(
        # counted as int rather than bigint: Postgres sends bigint as text, to
        # keep the precision JSON numbers would lose
        "select r.id, r.started_at, r.mode, r.max_actions,"
        " count(g.game)::int as games, count(g.finished_at)::int as done,"
        " sum(g.score)::int as levels, sum(g.actions_used)::int as actions,"
        " sum(g.cost_usd) as cost"
        " from runs r left join games g on g.run = r.id"
        " group by r.id order by r.started_at desc limit $1",
        args.limit,
    )
    print(f"{'run':<22} {'started':<20} {'mode':<8} games  levels  actions    cost")
    for r in rows:
        print(
            f"{r['id']:<22} {str(r['started_at'])[:19]:<20} {r['mode']:<8}"
            f" {r['done']:>2}/{r['games']:<3} {r['levels'] or 0:>6} {r['actions'] or 0:>8}"
            f"  ${float(r['cost'] or 0):>6.2f}"
        )


def show(args: argparse.Namespace) -> None:
    rows = sql(
        "select *, extract(epoch from now() - updated_at)::int as stale"
        " from games where run = $1 order by game",
        args.run,
    )
    if not rows:
        raise SystemExit(f"db: no run {args.run}")
    print(f"{'game':<16} {'levels':<8} {'actions':>8}  {'state':<13} {'cost':>7}  seen")
    for r in rows:
        cost = f"${r['cost_usd']:.2f}" if r["cost_usd"] else ""
        print(
            f"{r['game']:<16} {r['score']:>2}/{r['win_levels']:<5} {r['actions_used']:>8}"
            f"  {r['state']:<13} {cost:>7}  {int(r['stale'])}s"
        )
    done = sum(1 for r in rows if r["finished_at"])
    cost = sum(r["cost_usd"] or 0 for r in rows)
    print(
        f"\n{done}/{len(rows)} finished, {sum(r['score'] for r in rows)} levels, "
        f"{sum(r['actions_used'] for r in rows)} actions, ${cost:.2f}"
    )
    dirty = [r["game"] for r in rows if r["audit"] and r["audit"].get("findings")]
    if dirty:
        print(f"AUDIT FAILED: {', '.join(dirty)}")


def pull(args: argparse.Namespace) -> None:
    """Bring a run's workspaces back onto this disk, from the database alone."""
    root = RUNS / args.run
    rows = sql(
        "select game, name, encode(body,'base64') as body from artifacts where run = $1"
        " order by game, name",
        args.run,
    )
    if not rows:
        raise SystemExit(f"db: no artifacts for {args.run}")
    for r in rows:
        path = root / r["game"] / r["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.decompress(b64decode(r["body"])))
    games = len({r["game"] for r in rows})
    print(f"{len(rows)} files across {games} games -> {root}")


def query(args: argparse.Namespace) -> None:
    for row in sql(args.statement):
        print(json.dumps(row, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(prog="db", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the tables").set_defaults(func=init)

    p = sub.add_parser("ls", help="runs, newest first")
    p.add_argument("--limit", type=int, default=1000, help="how many runs to show")
    p.set_defaults(func=ls)

    p = sub.add_parser("show", help="a run's games")
    p.add_argument("run")
    p.set_defaults(func=show)

    p = sub.add_parser("pull", help="a run's artifacts, back onto this disk")
    p.add_argument("run")
    p.set_defaults(func=pull)

    p = sub.add_parser("q", help="run a statement and print rows as JSON")
    p.add_argument("statement")
    p.set_defaults(func=query)

    p = sub.add_parser("mirror", help="keep mirroring a workspace until killed")
    p.add_argument("run")
    p.add_argument("game")
    p.add_argument("workspace")
    p.add_argument("--every", type=int, default=MIRROR_EVERY)
    p.set_defaults(func=follow)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
