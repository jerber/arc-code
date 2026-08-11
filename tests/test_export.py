"""Tests for the export scrubber.

The export is the only thing standing between a live credential in the database
and a public archive, so the rules that decide what leaves are pinned here.
Every case below is a real shape found in the record.
"""

import gzip
import json
import re

import export


def test_a_cookie_bearing_file_is_caught_whatever_it_is_called():
    """The agents renamed two of these themselves — `scorecard-dead.json` and
    `old_run/state.json` — so the rule has to read the body, not the name."""
    body = json.dumps({"card_id": "c1", "cookies": {"GAMESESSION": "a" * 64}}).encode()
    assert export.carries_cookies(body)
    assert export.carries_cookies(b"not json at all") is None
    assert export.carries_cookies(b'{"score": 97.3}') is None


def test_a_file_whose_cookies_are_empty_is_kept():
    """Fourteen of these exist. They carry a score and an action count and no
    credential, and a filename rule would have deleted them for nothing."""
    assert export.carries_cookies(json.dumps({"score": 9, "cookies": {}}).encode()) is None


def test_the_cookie_value_goes_but_the_behaviour_stays_legible():
    """One flagged session is flagged *because* it read cookies out of the
    workspace, and the README quotes that finding. Redacting the name as well
    as the value would delete the evidence for a published claim."""
    value = "de" * 32
    out = export.scrub(f'session.cookies.set("GAMESESSION", "{value}")', {value})
    assert value not in out
    assert "GAMESESSION" in out, "the finding must survive its own redaction"
    assert export.REDACTED in out


def test_a_truncated_copy_of_a_cookie_is_still_removed():
    """Terminal renders cut long values mid-token, so an exact-value pass alone
    leaves a usable prefix behind."""
    value = "ab" * 32
    assert value[:40] not in export.scrub(f"cookie was {value[:40]}...", {value})


def test_a_cookie_never_stored_here_is_caught_by_shape():
    """A value can appear in a stream without the file that held it surviving."""
    out = export.scrub('{"GAMESESSION": "0123456789abcdef0123456789abcdef"}', set())
    assert "0123456789abcdef" not in out


def test_an_emptied_cookie_is_kept_because_it_is_information():
    """The server writes `_remove_` when it expires a session; hiding that would
    hide why the run then failed."""
    assert "_remove_" in export.scrub('{"AWSALBAPP-0": "_remove_"}', set())


def test_signatures_are_blanked_and_the_reasoning_is_not():
    text = '{"type":"thinking","thinking":"the door is at 10,10","signature":"' + "A" * 200 + '"}'
    out = export.scrub(text, set())
    assert '"signature":""' in out
    assert "the door is at 10,10" in out, "the reasoning is the evidence"


def test_sandbox_hosts_and_the_operator_path_are_generalised():
    out = export.scrub("curl https://8000-icopu8tvg97g2cd8qhadq.e2b.app/act", set())
    assert "e2b.app" not in out and "<BROKER-HOST>" in out
    assert export.scrub("cd /home/user/arcsec/runs", set()) == "cd /arcsec/runs"


def test_the_verifier_rejects_every_credential_shape(tmp_path):
    """The gate. If this stops firing, a bad archive ships silently. The model
    keys the runs used are not all still to hand, so these are shapes rather
    than values — including a catch-all for an assignment we did not predict."""
    for label, sample in [
        ("anthropic", "sk-ant-" + "a" * 40),
        ("openai", "sk-proj-" + "b" * 40),
        ("openai plain", "sk-" + "c" * 40),
        ("e2b", "e2b_" + "d" * 32),
        ("github", "github_pat_" + "e" * 40),
        ("dsn", "postgres://user:pw@ep-x.neon.tech/db"),
        ("bearer", "Bearer " + "f" * 40),
        ("sandbox", "8000-icopu8tvg97g2cd8qhadq.e2b.app"),
        ("cookie", 'GAMESESSION": "' + "0" * 40),
        ("unknown-shape key", 'OPENAI_API_KEY="zzzz-9999-not-a-known-prefix-aaaa"'),
    ]:
        path = tmp_path / "sample.txt"
        path.write_text(sample)
        assert export.offenders(path), f"{label} slipped past the verifier"
        path.unlink()

    clean = tmp_path / "fine.txt"
    clean.write_text('{"GAMESESSION": "<REDACTED>"}\n./act do ACTION1 --plan "probe"\n')
    assert export.offenders(clean) == []
    assert export.clean_tree(tmp_path)


class Recorder:
    """Stands in for Postgres, keeping every statement it was asked to send."""

    def __init__(self):
        self.statements = []

    def batch(self, statements):
        self.statements.extend(statements)


def test_load_numbers_its_parameters_correctly(monkeypatch, tmp_path):
    """`load` is the first thing a reader runs, and it had never been executed.
    An insert built from a variable column list is exactly the shape that goes
    off by one, and it only fails against a real database."""
    (tmp_path / "runs.jsonl").write_text(
        json.dumps({"id": "sealed3", "mode": "online", "model": "claude-opus-5",
                    "max_actions": 2500, "note": None}) + "\n"
    )
    (tmp_path / "games.jsonl").write_text(
        json.dumps({"run": "sealed3", "game": "bp35", "state": "WIN", "score": 9}) + "\n"
    )
    (tmp_path / "actions.jsonl").write_text(
        json.dumps({"run": "sealed3", "game": "bp35", "n": 1, "level": 1,
                    "attempt": 1, "score": 0, "action": "RESET"}) + "\n"
    )
    ws = tmp_path / "artifacts" / "sealed3" / "bp35"
    ws.mkdir(parents=True)
    (ws / "notes.md").write_text("what I learned")

    recorder = Recorder()
    monkeypatch.setattr(export.db, "batch", recorder.batch)
    export.load(type("Args", (), {"path": str(tmp_path)})())

    assert recorder.statements, "nothing was sent"
    for query, params in recorder.statements:
        wanted = {int(n) for n in re.findall(r"\$(\d+)", query)}
        assert wanted == set(range(1, len(params) + 1)), f"{query} got {len(params)} parameters"

    # A null column must be omitted rather than sent, so the table's own default
    # applies instead of a null overwriting it.
    runs = next(q for q, _ in recorder.statements if q.startswith("insert into runs"))
    assert "note" not in runs

    art = next(p for q, p in recorder.statements if q.startswith("insert into artifacts"))
    assert art[:3] == ("sealed3", "bp35", "notes.md")
    assert gzip.decompress(art[4]) == b"what I learned", "bodies are stored gzipped"


def test_table_rows_are_scrubbed_like_artifacts(monkeypatch, tmp_path):
    """A row is not structurally safer than a file.

    games.reaudit stores the commands an audit flagged, and a session that
    probed its own broker put that address into the record. The tables path
    wrote rows straight through until verify caught it on the first build that
    had one.
    """
    rows = {
        "runs": [{"id": "r", "note": "cookie=SECRETCOOKIEVALUE0123456789"}],
        "games": [{"run": "r", "game": "g", "reaudit": "curl https://8000-abcdefghijklmnopqrst.e2b.app/health"}],
        "actions": [{"run": "r", "game": "g", "n": 1}],
    }

    def fake_sql(query, *params):
        for name in ("runs", "games", "actions"):
            if f"from {name}" in query:
                return rows[name]
        return []

    monkeypatch.setattr(export.db, "sql", fake_sql)
    export.tables(tmp_path, ["r"], {"SECRETCOOKIEVALUE0123456789"})

    games = (tmp_path / "games.jsonl").read_text()
    assert "e2b.app" not in games, "a sandbox host reached the shipped tables"
    assert "<BROKER-HOST>" in games, "the finding should survive, generalised"
    assert "SECRETCOOKIEVALUE0123456789" not in (tmp_path / "runs.jsonl").read_text()


def test_the_broker_token_is_scrubbed_and_refused():
    """Every agent has the broker's token in its environment — it needs it to
    reach the broker. A session ran `env` and published it into its trace, and
    the pattern list did not know the name, so verify shipped it."""
    dump = 'ARCSEC_BROKER=https://8000-abcdefghijklmnopqrst.e2b.app\\nARCSEC_TOKEN=6e891445d6239c1321da65a0dc2358e9\\n'
    assert export.FORBIDDEN["broker token"].search(dump), "verify must refuse a raw token"
    clean = export.scrub(dump, set())
    assert "6e891445d6239c1321da65a0dc2358e9" not in clean
    assert "ARCSEC_TOKEN" in clean, "the variable stays; only its value goes"
    assert not export.FORBIDDEN["broker token"].search(clean)
