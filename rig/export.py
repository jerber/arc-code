#!/usr/bin/env python3
"""Build a publishable copy of the record, and refuse to ship a bad one.

The database is the evidence, but it is not publishable as it stands: four
pre-broker runs carry a live ARC session cookie, in their own `state.json` and
`scorecard.json` and again inside the agent streams that read those files. So
publishing is not `db.py pull` with a tarball around it — `pull` is the recovery
tool and stays byte-exact. This is the other thing: a lossy, deliberate copy.

    uv run export.py build                  # everything, into export/
    uv run export.py build --runs sealed3   # or just one
    uv run export.py verify export          # scan a built tree for credentials
    uv run export.py load export            # load a bundle into your own Postgres

`build` runs `verify` on its own output and exits non-zero if anything survives,
because the only safe assumption about a scrubber is that it missed something.
Run `verify` again on the unpacked archive before uploading it anywhere.

What is removed, and why:

* Any artifact whose body is JSON carrying a non-empty top-level `cookies` key.
  A content rule rather than a filename list: two of these files were renamed by
  the agents themselves (`scorecard-dead.json`, `old_run/state.json`), so a list
  of names would have shipped them. Files whose `cookies` is empty are kept —
  they hold a score and an action count and no credential.
* The cookie values, wherever else they appear — mostly agent streams, where
  sessions read their own `state.json` into context.
* Claude's `signature` fields: opaque tokens that exist only to replay a thinking
  block back to the API. They are 41% of all stream bytes and incompressible.
  The reasoning itself lives in the adjacent `thinking` field and is kept.
* Sandbox hostnames and the operator's home directory, which are noise.
* `__pycache__`, which is bytecode and not evidence.

What is deliberately kept: every command every agent ran, every file it wrote,
every board, and all seven sessions the audit flagged — including the two that
read cookies out of the workspace. Their findings are quoted in the README, so
the behavior has to stay legible even though the values do not.
"""

import argparse
import csv
import gzip
import hashlib
import json
import re
import shutil
import tarfile
from base64 import b64decode
from pathlib import Path

import db

REPO = Path(__file__).resolve().parent
OUT = REPO.parent / "export"

# Neon answers over HTTP and caps a response at 64 MB. Bodies travel base64, so
# a batch is budgeted on the encoded size with room to spare.
BUDGET = 24 * 1024 * 1024

# Cookies the game API sets. The value shapes differ — the session id is hex,
# the load-balancer cookies are base64url — so each gets its own pattern.
COOKIES = {
    "GAMESESSION": r"[0-9a-fA-F]{16,64}",
    "AWSALBAPP-0": r"[A-Za-z0-9+/=_-]{16,400}",
    "AWSALBAPP-1": r"[A-Za-z0-9+/=_-]{16,400}",
    "AWSALB": r"[A-Za-z0-9+/=_-]{16,400}",
    "AWSALBCORS": r"[A-Za-z0-9+/=_-]{16,400}",
}
# A cookie named in the record but deliberately emptied by the server. Redacting
# it would hide that the server had expired the session, which is information.
KEEP = ("_remove_",)

REDACTED = "<REDACTED>"
# Long enough that a fragment this size is the credential and not a coincidence.
FRAGMENT = 32

SUBSTITUTIONS = (
    # Sandboxes that died hours after each run. The shim is the evidence a run
    # was brokered, so it is published with the address generalised rather than
    # dropped.
    (re.compile(r"\b\d{4}-[a-z0-9]{18,26}\.e2b\.(?:app|dev)\b"), "<BROKER-HOST>"),
    (re.compile(r"/home/user/arcsec\b"), "/arcsec"),
    # The broker's bearer token, which is in every agent's environment by
    # design — the agent needs it to reach the broker at all. Sessions run `env`
    # for their own reasons and one of them published it into its trace. Dead on
    # arrival (the sandbox it authenticated to is gone, and its address is
    # generalised above), but a token is a token.
    (
        re.compile(r"(ARCSEC_TOKEN[\"'\s:=]{1,8})[A-Za-z0-9_-]{16,}"),
        rf"\1{REDACTED}",
    ),
    # Opaque replay tokens; see the module docstring.
    (re.compile(r'("signature"\s*:\s*")[^"]{16,}(")'), r"\1\2"),
)

# What `verify` refuses to ship. Matched against every byte of the built tree.
#
# These are shapes, not values: the model keys the runs used are not all still
# to hand, so a value list would check only what we happen to hold. The shapes
# cover every provider credential the agents' environments ever carried.
FORBIDDEN = {
    "anthropic key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "openai key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}"),
    "e2b key": re.compile(r"\be2b_[A-Za-z0-9]{20,}"),
    "github token": re.compile(
        r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"
    ),
    "aws key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    "daytona key": re.compile(r"\bdtn_[A-Za-z0-9]{20,}"),
    "modal token": re.compile(r"\bak-[A-Za-z0-9]{20,}|\bas-[A-Za-z0-9]{20,}"),
    "postgres dsn": re.compile(r"postgres(?:ql)?://[^\s\"']{16,}"),
    "neon host": re.compile(r"\b[\w.-]+\.neon\.tech\b"),
    "bearer token": re.compile(r"Bearer\s+[0-9a-fA-F]{32,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "sandbox host": re.compile(r"\b\d{4}-[a-z0-9]{18,26}\.e2b\.(?:app|dev)\b"),
    "operator path": re.compile(r"/home/user/"),
    # An assignment of any credential variable to something that is not empty
    # and not a placeholder — catches a key whose shape we did not anticipate.
    "key assignment": re.compile(
        r"(?:ANTHROPIC|OPENAI|ARC|E2B|DAYTONA)_API_KEY[\"'\s:=]{1,8}[A-Za-z0-9_\-]{20,}"
    ),
    "broker token": re.compile(r"ARCSEC_TOKEN[\"'\s:=]{1,8}[A-Za-z0-9_-]{16,}"),
    **{
        f"{name} cookie": re.compile(rf"{re.escape(name)}[\"'\s:=/]{{0,12}}{shape}")
        for name, shape in COOKIES.items()
    },
}


# --------------------------------------------------------------------------- #
# Reading the record
# --------------------------------------------------------------------------- #


def holes(count: int, start: int = 1) -> str:
    """`$1,$2,...` — db.encode turns a list into JSON, which Postgres will not
    read as an array, so every element travels as its own parameter."""
    return ",".join(f"${i}" for i in range(start, start + count))


def index(runs: list[str] | None) -> list[dict]:
    """Every artifact worth shipping, with its stored size, in a stable order.

    Sizes come back with the listing so bodies can be batched to a budget
    without asking twice.
    """
    where = f"where run in ({holes(len(runs))})" if runs else ""
    rows = db.sql(
        "select run, game, name, octet_length(body) as stored"
        f" from artifacts {where} order by run, game, name",
        *(runs or []),
    )
    return [r for r in rows if "__pycache__" not in r["name"]]


def bodies(rows: list[dict]):
    """Artifact bodies, fetched in batches small enough to come back.

    Grouped by run and game and cut at a byte budget: one request per artifact
    would be thousands of round trips, one request for everything exceeds the
    endpoint's response cap.
    """
    batch: list[dict] = []
    size = 0
    for row in rows:
        same = batch and (batch[0]["run"], batch[0]["game"]) == (row["run"], row["game"])
        if batch and (not same or size + row["stored"] * 4 // 3 > BUDGET):
            yield from fetch(batch)
            batch, size = [], 0
        batch.append(row)
        size += row["stored"] * 4 // 3
    if batch:
        yield from fetch(batch)


def fetch(batch: list[dict]):
    """One request for a contiguous slice of one game's artifacts."""
    first = batch[0]
    got = db.sql(
        "select name, encode(body,'base64') as body from artifacts"
        f" where run = $1 and game = $2 and name in ({holes(len(batch), 3)})",
        first["run"],
        first["game"],
        *(r["name"] for r in batch),
    )
    have = {r["name"]: r["body"] for r in got}
    for row in batch:
        raw = have.get(row["name"])
        if raw is None:
            where = f"{row['run']}/{row['game']}/{row['name']}"
            raise SystemExit(f"export: {where} vanished mid-export")
        yield row, gzip.decompress(b64decode(raw))


# --------------------------------------------------------------------------- #
# Deciding what leaves
# --------------------------------------------------------------------------- #


def carries_cookies(body: bytes) -> dict | None:
    """The cookies in this artifact, if it is JSON that holds any.

    Content rather than filename: the agents renamed two of these themselves,
    and a name list would have shipped exactly the files that matter. An empty
    `cookies` is not a finding — that file is a score and an action count.
    """
    if len(body) > 1 << 20 or body.lstrip()[:1] not in (b"{", b"["):
        return None
    try:
        got = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    found = got.get("cookies") if isinstance(got, dict) else None
    return found if isinstance(found, dict) and found else None


def scrub(text: str, values: set[str]) -> str:
    """Remove the credentials, keep the behavior.

    Three layers, because none alone is enough. Exact values catch what was
    stored; prefixes catch the copies a terminal truncated mid-token; the
    name-anchored shapes catch a value that was never stored here at all.
    """
    for value in sorted(values, key=len, reverse=True):
        if value in KEEP:
            continue
        text = text.replace(value, REDACTED)
        # A truncated render leaves a prefix, which no exact match will find.
        for cut in range(len(value) - 1, FRAGMENT - 1, -1):
            piece = value[:cut]
            if piece in text:
                text = text.replace(piece, REDACTED)
                break
    for name, shape in COOKIES.items():
        text = re.sub(
            rf"({re.escape(name)}[\"'\s:=/]{{0,12}})(?!{'|'.join(KEEP)}){shape}",
            rf"\1{REDACTED}",
            text,
        )
    for pattern, replacement in SUBSTITUTIONS:
        text = pattern.sub(replacement, text)
    return text


def harvest(rows: list[dict]) -> set[str]:
    """Every cookie value in the record, so it can be removed from everywhere.

    Collected in a first pass: a value has to be known before the streams that
    quote it can be cleaned, and the files holding them are about to be dropped.
    """
    values: set[str] = set()
    for _, body in bodies([r for r in rows if r["name"].endswith(".json")]):
        found = carries_cookies(body)
        if found:
            values |= {str(v) for v in found.values() if isinstance(v, str) and len(v) >= 16}
    return values


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

TABLES = (("runs", "id"), ("games", "run"))


def tables(out: Path, runs: list[str] | None, values: set[str]) -> dict[str, int]:
    """The record's own tables, as JSONL.

    This is the half that makes the numbers checkable: `actions` is where the
    per-level counts come from, and without it a reader has traces but no way to
    recompute a score. Fetched a run at a time because it is six figures of rows.

    Scrubbed like the artifacts, and for the same reason. A row is not
    structurally safer than a file: `games.reaudit` stores the commands an audit
    flagged, and a session that probed its own broker put that address in the
    record. This path used to write rows straight through, and `verify` caught
    the leak on the build that first had one.
    """
    counts = {}
    for table, column in TABLES:
        where = f"where {column} in ({holes(len(runs))})" if runs else ""
        rows = db.sql(f"select * from {table} {where} order by 1", *(runs or []))
        (out / f"{table}.jsonl").write_text(
            "".join(scrub(json.dumps(r, default=str), values) + "\n" for r in rows)
        )
        counts[table] = len(rows)

    names = runs or [r["id"] for r in db.sql("select id from runs order by id")]
    written = 0
    with (out / "actions.jsonl").open("w") as handle:
        for name in names:
            for row in db.sql("select * from actions where run = $1 order by game, n", name):
                handle.write(scrub(json.dumps(row, default=str), values) + "\n")
                written += 1
    counts["actions"] = written
    return counts


def build(args: argparse.Namespace) -> None:
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "artifacts").mkdir(parents=True)

    rows = index(args.runs)
    if not rows:
        raise SystemExit(f"export: nothing to export for {args.runs or 'any run'}")
    print(f"{len(rows)} artifacts across {len({(r['run'], r['game']) for r in rows})} sessions")

    print("harvesting cookie values ...", end=" ", flush=True)
    values = harvest(rows)
    print(f"{len(values)} distinct value(s) to remove")

    manifest, dropped, scrubbed, total = [], 0, 0, 0
    for row, body in bodies(rows):
        if carries_cookies(body):
            dropped += 1
            continue
        try:
            text = body.decode()
        except UnicodeDecodeError:
            clean = body  # not text; nothing to scrub and nothing that hides a key
        else:
            fixed = scrub(text, values)
            scrubbed += fixed != text
            clean = fixed.encode()
        path = out / "artifacts" / row["run"] / row["game"] / row["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(clean)
        total += len(clean)
        manifest.append(
            {
                "run": row["run"],
                "game": row["game"],
                "name": row["name"],
                "bytes": len(clean),
                "sha256": hashlib.sha256(clean).hexdigest(),
                "scrubbed": clean != body,
            }
        )
    print(f"{len(manifest)} written, {dropped} dropped as cookie-bearing, {scrubbed} scrubbed")

    counts = tables(out, args.runs, values)
    print(f"tables: {counts['runs']} runs, {counts['games']} games, {counts['actions']:,} actions")

    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    catalogue(out)
    checksums(out)
    (out / "README.md").write_text(bundle_readme(manifest, total))

    print(f"\nverifying {out} ...")
    if not clean_tree(out):
        raise SystemExit("export: the built tree still contains credential shapes — NOT shippable")
    print("verify: clean")

    if args.archive:
        archive = Path(str(out) + ".tar.gz")
        with tarfile.open(archive, "w:gz", compresslevel=9) as tar:
            tar.add(out, arcname=out.name)
        size = archive.stat().st_size
        print(f"\n{archive}  {size / 1e6:.1f} MB compressed, {total / 1e6:.0f} MB unpacked")


# The two records every session writes. They are large and nobody reads them
# by eye, so they are the only files gzipped; everything else is what the agent
# wrote and should render in a browser.
GZIP = ("logs.txt", "agent_stream.jsonl")


def pick(args: argparse.Namespace) -> None:
    """Copy single sessions out as readable folders.

    The bundle is the record; this is for the handful of sessions the README
    points at, so a reader can open the notes and the scripts without
    downloading a gigabyte. The workspace is kept flat because the agent's own
    files assume it — `auto.py` imports `parse` from beside it, and `notes.md`
    refers to `drive.py` by name — so re-sorting into subdirectories would break
    what it is supposed to show.
    """
    out = Path(args.out)
    for spec in args.sessions:
        game, _, run = spec.partition("@")
        if not run:
            raise SystemExit(f"export: {spec!r} should be <game>@<run>, e.g. lf52@lf52-r1")
        rows = [r for r in index([run]) if r["game"].startswith(game)]
        if not rows:
            raise SystemExit(f"export: no session for game {game!r} in run {run!r}")
        full = rows[0]["game"]
        folder = out / f"{game}_{run}"
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)

        values = harvest(rows)
        kept = 0
        for row, body in bodies(rows):
            if carries_cookies(body):
                continue
            try:
                clean = scrub(body.decode(), values).encode()
            except UnicodeDecodeError:
                continue  # not text, and not something a reader would open
            name = row["name"]
            if name in GZIP:
                with gzip.open(folder / f"{name}.gz", "wb") as f:
                    f.write(clean)
            else:
                (folder / name).write_bytes(clean)
            kept += 1
        print(f"{folder.name}: {kept} files from {full}")

    if not clean_tree(out):
        raise SystemExit("export: pick wrote something that looks like a credential")
    print(f"\nverify: clean — {out}")


def catalogue(out: Path) -> None:
    """One row per session, so the bundle can be read without a database."""
    rows = [json.loads(line) for line in (out / "games.jsonl").read_text().splitlines() if line]
    fields = [
        "run", "game", "agent", "model", "state", "score", "win_levels",
        "actions_used", "max_actions", "cost_usd", "turns", "seconds",
    ]
    with (out / "index.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([*fields, "audit_findings"])
        for row in sorted(rows, key=lambda r: (r["run"], r["game"])):
            verdict = row.get("reaudit") or row.get("audit") or {}
            if isinstance(verdict, str):
                verdict = json.loads(verdict)
            findings = ";".join((verdict or {}).get("findings", {})) or "none"
            writer.writerow([*(row.get(f, "") for f in fields), findings])


def checksums(out: Path) -> None:
    lines = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(out)}")
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def offenders(path: Path) -> list[str]:
    """Which forbidden shapes appear in one file. Never returns the match."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    return [label for label, pattern in FORBIDDEN.items() if pattern.search(text)]


def clean_tree(root: Path) -> bool:
    bad = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        for label in offenders(path):
            print(f"  LEAK  {label:20} {path.relative_to(root)}")
            bad += 1
    return bad == 0


def verify(args: argparse.Namespace) -> None:
    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"export: no such path {root}")
    files = sum(1 for p in root.rglob("*") if p.is_file())
    print(f"scanning {files} files under {root}")
    if not clean_tree(root):
        raise SystemExit("export: credential shapes found — do not publish this")
    print("verify: clean")


def load(args: argparse.Namespace) -> None:
    """Load a published bundle into your own Postgres.

    The verification commands read the database, so reproducing a number means
    putting the record back into one. `db.py init` first.
    """
    root = Path(args.path)
    for table, _ in TABLES:
        text = (root / f"{table}.jsonl").read_text().splitlines()
        rows = [json.loads(line) for line in text if line]
        send(table, rows)
        print(f"{table}: {len(rows)} rows")
    actions = [json.loads(line) for line in (root / "actions.jsonl").open() if line.strip()]
    send("actions", actions)
    print(f"actions: {len(actions):,} rows")

    files = sorted(p for p in (root / "artifacts").rglob("*") if p.is_file())
    for i in range(0, len(files), 40):
        db.batch([
            (
                "insert into artifacts (run, game, name, bytes, body)"
                " values ($1,$2,$3,$4,decode($5,'base64'))"
                " on conflict (run, game, name) do update"
                " set bytes = excluded.bytes, body = excluded.body",
                (
                    p.relative_to(root / "artifacts").parts[0],
                    p.relative_to(root / "artifacts").parts[1],
                    "/".join(p.relative_to(root / "artifacts").parts[2:]),
                    p.stat().st_size,
                    gzip.compress(p.read_bytes()),
                ),
            )
            for p in files[i : i + 40]
        ])
    print(f"artifacts: {len(files)} files")
    print("\nloaded — now: uv run score.py verify")


def send(table: str, rows: list[dict]) -> None:
    """Insert rows, chunked, with the columns the bundle actually carries."""
    for i in range(0, len(rows), 200):
        chunk = rows[i : i + 200]
        statements = []
        for row in chunk:
            columns = [k for k, v in row.items() if v is not None]
            slots = ",".join(f"${n}" for n in range(1, len(columns) + 1))
            statements.append(
                (
                    f"insert into {table} ({','.join(columns)}) values ({slots})"
                    " on conflict do nothing",
                    tuple(row[c] for c in columns),
                )
            )
        db.batch(statements)


def bundle_readme(manifest: list[dict], total: int) -> str:
    sessions = len({(m["run"], m["game"]) for m in manifest})
    return f"""# arc-code — the record

Every session selected for this bundle, as the harness stored it.
{sessions} sessions, {len(manifest)} files, {total / 1e6:.0f} MB unpacked.

## Layout

    artifacts/<run>/<game>/     one directory per session
      logs.txt                  the programmatic memory: every action and the
                                board it produced, appended by code
      agent_stream.jsonl        the agent's complete event stream — every
                                command it ran and every file it wrote
      notes.md                  whatever the agent chose to keep
      report.json               cost, turns, tokens, and the audit verdict
      *.py                      tools the agent wrote for itself
    runs.jsonl games.jsonl actions.jsonl    the record's own tables
    index.csv                   one row per session: score, actions, cost, audit
    manifest.json SHA256SUMS    what is here, and its checksums

## Checking the numbers yourself

The verification commands read a database, so put the record into one:

    createdb / create a free Neon project, then
    export POSTGRES_DSN=postgres://...
    uv run db.py init
    uv run export.py load .
    uv run score.py verify        # the formula against every score ARC disclosed
    uv run audit.py record        # re-grade every session's trace

## The two stream formats

`agent_stream.jsonl` is whatever the CLI emitted, unmodified except as below.
The two agents differ: Claude Code writes `system` / `assistant` / `user` /
`result` events, with reasoning in `thinking` blocks; Codex writes
`thread.started` / `item.completed` / `turn.completed`, and has no thinking
blocks. `report.json` names which agent played.

## What was removed

* Artifacts holding live session cookies — `state.json` and `scorecard.json`
  from the four pre-broker runs, plus two the agents renamed themselves. The
  cookie values are also redacted wherever a stream quoted them.
* Claude's `signature` fields, blanked. They are opaque tokens for replaying a
  thinking block back to the API, 41% of all stream bytes and incompressible.
  The reasoning text beside them is untouched.
* Sandbox hostnames and the operator's home directory, generalised.
* `__pycache__`.

Nothing else. Every command, every board, every note is as the run left it —
including the seven sessions the audit flagged, which are here on purpose.
"""


def main() -> int:
    parser = argparse.ArgumentParser(prog="export", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="build a publishable bundle")
    p.add_argument("--out", default=str(OUT))
    p.add_argument("--runs", nargs="+", help="only these runs (default: all)")
    p.add_argument("--archive", action="store_true", help="also write a .tar.gz")
    p.set_defaults(func=build)

    p = sub.add_parser("verify", help="scan a built tree for credential shapes")
    p.add_argument("path")
    p.set_defaults(func=verify)

    p = sub.add_parser("pick", help="copy single sessions out as readable folders")
    p.add_argument("sessions", nargs="+", metavar="GAME@RUN", help="e.g. lf52@lf52-r1")
    p.add_argument("--out", default="data/runs")
    p.set_defaults(func=pick)

    p = sub.add_parser("load", help="load a bundle into your own Postgres")
    p.add_argument("path")
    p.set_defaults(func=load)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
