"""Tests for the record.

Two things have to hold. The log parser must read back exactly what act.py
wrote — it is where the per-level action counts that scoring depends on come
from — and the statements must number their parameters correctly, because a
mirror that raises hours into a run is a run whose evidence never left the
sandbox.

Nothing here touches the network: the SQL layer is replaced by a recorder that
keeps what it was asked to send.
"""

import argparse
import gzip
import json
import re
from base64 import b64decode
from pathlib import Path

import db
import pytest

import act
from act import RunState, Step

BLANK = [[0] * 64 for _ in range(64)]


def played(ws: Path, steps: list[tuple[Step, int, int]], plan: str | None = None) -> RunState:
    """Write a log the way act.py writes one, so the parser is tested against
    the real format rather than against a fixture that can drift from it."""
    state = RunState(game_id="ls20-0000", plan=plan)
    act.log_initial(ws, state, [BLANK])
    for i, (step, level, score) in enumerate(steps, start=1):
        state.actions_used, state.level, state.score = i, level, score
        act.log_action(ws, state, step, [BLANK], i, len(steps))
    state.save(ws)
    return state


def test_the_parser_reads_back_what_the_actuator_wrote(tmp_path):
    played(
        tmp_path,
        [
            (Step(name="ACTION1"), 1, 0),
            (Step(name="ACTION6", x=38, y=46), 1, 1),
            (Step(name="RESET"), 2, 1),
        ],
        plan="probe the corner",
    )
    rows = db.parse_log(tmp_path / "logs.txt")

    assert [r["n"] for r in rows] == [0, 1, 2, 3], "the initial state is action 0"
    assert [r["action"] for r in rows] == ["INITIAL", "ACTION1", "ACTION6", "RESET"]
    assert [r["level"] for r in rows] == [1, 1, 1, 2]
    assert [r["score"] for r in rows] == [0, 0, 1, 1]
    assert (rows[2]["x"], rows[2]["y"]) == (38, 46)
    assert rows[1]["x"] is None, "a non-coordinate action carries no coordinates"
    assert rows[2]["plan"] == "probe the corner"
    assert rows[0]["plan"] is None, "there is nothing planned before the first action"


def test_a_multi_line_plan_survives_the_round_trip(tmp_path):
    played(tmp_path, [(Step(name="ACTION2"), 1, 0)], plan="first line\nsecond line")
    assert db.parse_log(tmp_path / "logs.txt")[1]["plan"] == "first line\nsecond line"


def test_per_level_counts_come_out_of_the_log(tmp_path):
    """The whole reason actions are rows: scoring is per level, and the log
    header is the only place the level of an action is recorded."""
    played(
        tmp_path,
        [(Step(name="ACTION1"), level, 0) for level in (1, 1, 1, 2, 2, 3)],
    )
    rows = [r for r in db.parse_log(tmp_path / "logs.txt") if r["action"] != "INITIAL"]
    counts = {level: sum(1 for r in rows if r["level"] == level) for level in (1, 2, 3)}
    assert counts == {1: 3, 2: 2, 3: 1}


def test_a_header_missing_a_field_is_an_error_not_a_guess():
    with pytest.raises(ValueError, match="no Level"):
        db.field("Action 3 | Attempt 1 | Score: 2", "Level")


def test_values_that_are_not_json_are_encoded_for_it():
    assert db.encode(7) == 7 and db.encode(None) is None
    assert json.loads(db.encode({"findings": {}})) == {"findings": {}}
    assert b64decode(db.encode(b"gzipped")) == b"gzipped"


class Recorder:
    """Stands in for Postgres: keeps every statement, and answers the two
    questions the mirror asks before it decides what to send."""

    def __init__(self, high: int = -1, stored: list[dict] | None = None) -> None:
        self.statements: list[tuple[str, tuple]] = []
        self.high = high  # the highest action already recorded
        self.stored = stored or []  # artifacts already there, as name and size

    def sql(self, query: str, *params):
        self.statements.append((query, params))
        if "max(n)" in query:
            return [{"high": self.high}]
        return self.stored if "from artifacts" in query else []

    def batch(self, statements):
        self.statements.extend(statements)

    def sent(self, table: str) -> list[tuple[str, tuple]]:
        return [s for s in self.statements if s[0].startswith(f"insert into {table}")]


@pytest.fixture
def install(monkeypatch):
    def use(recorder: Recorder) -> Recorder:
        monkeypatch.setattr(db, "sql", recorder.sql)
        monkeypatch.setattr(db, "batch", recorder.batch)
        return recorder

    return use


@pytest.fixture
def sent(install):
    return install(Recorder())


def test_every_statement_numbers_its_parameters(tmp_path, sent):
    """An `update ... set c = $3` built from a column list is exactly the kind
    of thing that is off by one, and it only fails against a real database."""
    played(tmp_path, [(Step(name="ACTION1"), 1, 0)])
    db.mirror("r", "ls20", tmp_path)
    db.finish_game("r", "ls20", tmp_path, {"cost_usd": 1.5, "audit": {"findings": {}}})
    db.open_run("r", "online", "claude-opus-5", 2500)
    db.open_game("r", "ls20", "host", 2500)
    db.record_official("r", ["ls20"], "card", {"score": 93})

    for query, params in sent.statements:
        wanted = {int(n) for n in re.findall(r"\$(\d+)", query)}
        assert wanted == set(range(1, len(params) + 1)), f"{query} got {len(params)} parameters"


def test_the_mirror_sends_the_state_the_game_reports(tmp_path, sent):
    state = played(tmp_path, [(Step(name="ACTION1"), 1, 0)])
    state.state, state.score, state.win_levels = "WIN", 7, 7
    state.save(tmp_path)

    db.mirror("r", "ls20", tmp_path)
    update = next(s for s in sent.statements if s[0].startswith("update games"))
    assert update[1][:2] == ("r", "ls20")
    assert dict(zip(db.LIVE, update[1][2:], strict=True))["state"] == "WIN"


def test_only_actions_the_database_has_not_seen_are_sent(tmp_path, install):
    played(tmp_path, [(Step(name="ACTION1"), 1, 0) for _ in range(5)])
    recorder = install(Recorder(high=3))

    db.push_actions("r", "ls20", tmp_path / "logs.txt")
    assert [s[1][2] for s in recorder.sent("actions")] == [4, 5], "0-3 were already recorded"


def test_a_slice_of_log_is_recorded_without_reading_the_rest(tmp_path, install):
    """The broker knows what act.py just wrote, so it sends only that. Parsing
    a log that reaches tens of megabytes after every action would not stay
    cheap, and it runs for every game in the batch at once."""
    played(tmp_path, [(Step(name="ACTION1"), 1, 0) for _ in range(4)])
    whole = (tmp_path / "logs.txt").read_text()
    tail = whole[whole.index(f"\n{act.SEP}\naction 3") :]
    recorder = install(Recorder())

    db.push_slice("r", "ls20", tail)

    assert [s[1][2] for s in recorder.sent("actions")] == [3, 4]
    assert not any("max(n)" in s[0] for s in recorder.statements), "no round trip to ask how far"


def test_only_files_that_changed_are_uploaded(tmp_path, install):
    (tmp_path / "notes.md").write_text("same")
    (tmp_path / "logs.txt").write_text("grown")
    recorder = install(Recorder(stored=[{"name": "notes.md", "bytes": 4}]))

    db.push_artifacts("r", "ls20", tmp_path)
    uploads = recorder.sent("artifacts")
    assert [s[1][2] for s in uploads] == ["logs.txt"]
    _, size, body = uploads[0][1][2:]
    assert size == 5, "the stored size is the file's, not the compressed one's"
    assert gzip.decompress(body) == b"grown"


def test_an_adopted_game_stops_mirroring_when_its_session_ends(tmp_path, sent):
    """`follow` runs beside a launcher that will never tell it anything, so
    report.json appearing is the only signal that the game is over. Without it
    the loop outlives the game and the run never reads as finished."""
    played(tmp_path, [(Step(name="ACTION1"), 1, 0)])
    (tmp_path / "report.json").write_text(json.dumps({"cost_usd": 2.0, "turns": 41}))

    db.follow(argparse.Namespace(run="r", game="ls20", workspace=str(tmp_path), every=9999))
    final = next(s for s in sent.statements if "finished_at = now()" in s[0])
    assert dict(zip(db.FINAL, final[1][2:], strict=False))["cost_usd"] == 2.0


def test_a_file_the_agent_wrote_in_a_subdirectory_is_kept_too(tmp_path, sent):
    """Runs build themselves whole tool packages; the paths have to survive."""
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "solve.py").write_text("print(1)")

    (tmp_path / "tools" / "__pycache__").mkdir()
    (tmp_path / "tools" / "__pycache__" / "solve.pyc").write_bytes(b"\x00")

    db.push_artifacts("r", "ls20", tmp_path)
    kept = [s[1][2] for s in sent.sent("artifacts")]
    assert kept == ["tools/solve.py"], "bytecode is not evidence"


def test_v1_logs_still_parse():
    """The published bundle's logs are all v1; anyone verifying it parses them
    through this code, so the old format stays readable forever."""
    v1 = (
        "=" * 80 + "\n"
        "Action 0 | Level 1 | Attempt 1 | INITIAL STATE | Score: 0\n\n"
        "[INITIAL BOARD STATE]\nOfn$\n\n\n" + "=" * 80 + "\n"
        "Action 1 | Level 1 | Attempt 1 | Plan Step 1/1 | Score: 0\n\n"
        "\n[PLAN]\nprobe the corner\n\n"
        'Tool Call: ACTION6({"x": 30, "y": 40})\n'
        "[POST-ACTION BOARD STATE]\nOfn$\n\n"
    )
    first, second = db.parse_log_text(v1)
    assert first["action"] == "INITIAL" and first["n"] == 0
    assert second == {
        "n": 1, "level": 1, "attempt": 1, "score": 0,
        "action": "ACTION6", "x": 30, "y": 40, "plan": "probe the corner",
    }
