"""Tests for the broker and its client.

The guarantee is not that the agent uses the client — it can always call the
broker directly, and must be able to. The guarantee is that whatever reaches
the game is written down by the thing that forwards it, and that the agent's
local copy either matches or is repaired. These test that, and the byte
arithmetic the mirror depends on.
"""

import ast
import sys
from pathlib import Path

import broker
import client
import pytest


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "WORK", tmp_path)
    return tmp_path


def logged(work: Path, game: str, body: str) -> Path:
    ws = work / game
    ws.mkdir(parents=True, exist_ok=True)
    log = ws / broker.LOG
    log.write_text(body)
    return log


def test_the_tail_is_byte_exact_from_any_offset(work):
    """The client seeks by byte count, so an offset that means something else
    would corrupt every mirror after the first multi-byte character."""
    logged(work, "ft09", "héllo wörld")  # 13 bytes, 11 characters
    assert broker.tail("ft09", 0) == {"log": "héllo wörld", "size": 13}
    assert broker.tail("ft09", 7)["size"] == 13, "size counts bytes, not characters"
    assert broker.tail("ft09", 13) == {"log": "", "size": 13}


def test_a_game_that_has_not_started_has_an_empty_tail(work):
    assert broker.tail("nothing", 0) == {"log": "", "size": 0}


def test_the_broker_reports_what_the_actuator_did(work, monkeypatch):
    """Whatever act.py writes to the log between entering and leaving is what
    the client is handed — no bookkeeping in between to get out of step."""

    def actuator(cmd, cwd, capture_output, text):  # noqa: ARG001
        (Path(cwd) / broker.LOG).write_text("=" * 80 + "\nAction 1 | Level 1\n")
        return type("Done", (), {"stdout": "ran 1/1: ACTION1\n", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(broker.subprocess, "run", actuator)
    reply = broker.play("ft09", ["do", "ACTION1"])
    assert reply["rc"] == 0
    assert "ran 1/1" in reply["stdout"]
    assert "Action 1" in reply["log"]
    assert reply["size"] == len(reply["log"].encode())


def test_an_action_that_bypassed_the_client_is_still_in_the_record(work, monkeypatch):
    """The whole point. A direct call to the broker plays the action and the
    broker logs it, so the log stays complete whatever the agent does."""

    def actuator(cmd, cwd, capture_output, text):  # noqa: ARG001
        with (Path(cwd) / broker.LOG).open("a") as handle:
            handle.write(f"Action via {cmd[-1]}\n")
        return type("Done", (), {"stdout": "", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(broker.subprocess, "run", actuator)
    broker.play("ft09", ["do", "ACTION1"])
    broker.play("ft09", ["do", "BYPASS"])  # as if curled straight at the broker
    assert (work / "ft09" / broker.LOG).read_text().count("Action via") == 2


def test_only_init_opens_a_scorecard(work, monkeypatch):
    """Opening one needs the key and a live API. Only the first `init` should
    ask; a later command must join the card already saved in the workspace,
    never open a second one under a batch mid-play."""
    monkeypatch.setattr(
        broker, "scorecard", lambda: pytest.fail("only init may open a card")
    )
    monkeypatch.setattr(
        broker.subprocess,
        "run",
        lambda *a, **k: type("Done", (), {"stdout": "", "stderr": "", "returncode": 0})(),
    )
    broker.play("ft09", ["do", "ACTION1"])
    (work / "ft09" / broker.SCORECARD).write_text('{"card_id": "c", "cookies": {}}')
    broker.play("ft09", ["init", "ft09"])


class Broker:
    """A broker that answers from a script, to drive the client without HTTP."""

    def __init__(self, canonical: str) -> None:
        self.canonical = canonical
        self.asked: list[str] = []

    def call(self, path: str, body: dict | None = None) -> dict:
        self.asked.append(path)
        if path.startswith("/log"):
            offset = int(path.split("offset=")[1])
            rest = self.canonical.encode()[offset:]
            return {"log": rest.decode(), "size": len(self.canonical.encode())}
        return {"stdout": "", "rc": 0, "log": "", "size": len(self.canonical.encode())}


def test_a_mirror_that_has_fallen_behind_is_repaired(tmp_path, monkeypatch):
    """A local log can lag because it was edited, or because the broker was
    called without the client. Either way the next call restores it."""
    monkeypatch.chdir(tmp_path)
    Path(client.LOG).write_text("first half.")
    served = Broker("first half.and the rest the client never saw.")
    monkeypatch.setattr(client, "call", served.call)

    client.mirror({"log": "", "size": len(served.canonical.encode())})

    assert Path(client.LOG).read_text() == served.canonical
    assert any(p.startswith("/log") for p in served.asked), "it had to ask for the rest"


def test_a_mirror_that_agrees_is_left_alone(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(client.LOG).write_text("all of it.")
    served = Broker("all of it.")
    monkeypatch.setattr(client, "call", served.call)

    client.mirror({"log": "", "size": len("all of it.")})

    assert served.asked == [], "no catch-up needed, so no extra request"


def test_the_client_appends_what_it_was_handed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(client.LOG).write_text("so far.")
    served = Broker("so far. and this.")
    monkeypatch.setattr(client, "call", served.call)

    client.mirror({"log": " and this.", "size": len("so far. and this.")})

    assert Path(client.LOG).read_text() == "so far. and this."
    assert served.asked == []


def test_the_client_sends_the_arguments_it_was_given(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sent = {}

    def call(path, body=None):
        sent.update({"path": path, "body": body})
        return {"stdout": "ok\n", "rc": 3, "log": "", "size": 0}

    monkeypatch.setattr(client, "call", call)
    monkeypatch.setattr(sys, "argv", ["act", "do", "ACTION6:1,2", "--plan", "a plan"])

    assert client.main() == 3, "the actuator's exit code reaches the agent"
    assert sent["body"] == {"game": client.GAME, "argv": ["do", "ACTION6:1,2", "--plan", "a plan"]}


def test_the_card_closes_the_moment_the_last_game_is_home(monkeypatch):
    """ARC reaps an idle card in fifteen minutes, and a closed card is the only
    source of its own scoring. A sweep lost that: the last game finished,
    nothing closed the card, and half an hour later it was gone. Only the
    launcher can say a session ended — a game that stops with budget left looks
    exactly like one that is thinking — so it reports, and the last one closes."""
    closed = []
    monkeypatch.setattr(broker, "GAMES", ["a", "b"])
    monkeypatch.setattr(broker, "DONE", set())
    monkeypatch.setattr(broker, "close_card", lambda: closed.append(True) or {"closed": True})

    assert broker.finished("a") == {"closed": False, "waiting": ["b"]}
    assert not closed, "one still out"
    assert broker.finished("b") == {"closed": True}
    assert closed == [True]


def test_a_broker_told_of_no_games_never_closes_on_its_own(monkeypatch):
    """Without the list it cannot know when the batch is done, so it waits to be
    asked rather than closing the card under a game still playing."""
    monkeypatch.setattr(broker, "GAMES", [])
    monkeypatch.setattr(broker, "DONE", set())
    monkeypatch.setattr(broker, "close_card", lambda: pytest.fail("closed with no list"))
    assert broker.finished("a")["closed"] is False


def test_the_shim_works_without_help_from_the_environment(tmp_path):
    """A live run shipped a shim that left ARCSEC_GAME to the environment. It
    was set for the launcher and not for the agent, so `./act` failed and the
    agent wrote its own wrapper to supply it — the harness quietly depending on
    the agent papering over it. Everything the shim needs is in the shim."""
    import run

    ws = run.make_workspace(tmp_path, "ft09-0d8bbf25", "https://broker.example")
    shim = (ws / "act").read_text()
    assert 'ARCSEC_GAME="ft09-0d8bbf25"' in shim
    assert 'ARCSEC_BROKER="https://broker.example"' in shim
    assert (ws / "client.py").exists(), "and the client it runs is right there"


def test_a_workspace_without_a_broker_still_gets_the_actuator(tmp_path):
    import run

    shim = (run.make_workspace(tmp_path, "ft09", None) / "act").read_text()
    assert "act.py" in shim and "ARCSEC" not in shim


def test_the_client_can_read_nothing_but_where_the_broker_is():
    """The boundary, asserted directly: these three names are everything the
    client can take from its environment. If ARC_API_KEY ever joins them the
    agent's machine can reach the game again and the broker is decoration."""
    source = (Path(__file__).resolve().parents[1] / "rig" / "client.py").read_text()
    wanted = set()
    for node in ast.walk(ast.parse(source)):
        # os.environ["X"]
        if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ":
            wanted.add(ast.literal_eval(node.slice))
        # os.environ.get("X", ...)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "os.environ.get":
            wanted.add(ast.literal_eval(node.args[0]))
    assert wanted == {"ARCSEC_BROKER", "ARCSEC_GAME", "ARCSEC_TOKEN"}


def test_the_watchdog_waits_for_both_conditions(monkeypatch):
    """Two 25-game sweeps lost their official scores because the card closed on
    the last *session* exiting, while ARC reaps from the last *action* — and a
    session runs half an hour past its final action writing notes.

    So the card also closes on idleness. Both conditions are required: closing
    under a session that is merely thinking would fail its next action."""
    import broker

    games = ["ls20", "wa30"]
    monkeypatch.setitem(broker.STATE, "ls20", "WIN")
    monkeypatch.setitem(broker.STATE, "wa30", "GAME_OVER")

    assert broker.should_close(now=1000, last_action=0, games=games, idle=600)
    assert not broker.should_close(now=100, last_action=0, games=games, idle=600), (
        "still inside the idle window"
    )

    # one game still able to act — it may just be thinking hard
    monkeypatch.setitem(broker.STATE, "wa30", "NOT_FINISHED")
    assert not broker.should_close(now=1000, last_action=0, games=games, idle=600)

    # and a batch with no games named never closes on its own
    assert not broker.should_close(now=1000, last_action=0, games=[], idle=600)


def test_a_game_never_heard_from_is_not_assumed_spent(monkeypatch):
    """An unknown state means the broker has seen no action from that game. It
    could be starting up; closing the card under it would break it."""
    import broker

    monkeypatch.setattr(broker, "STATE", {"ls20": "WIN"})
    assert not broker.should_close(now=1e9, last_action=0, games=["ls20", "never_played"], idle=600)


def test_a_spent_budget_counts_as_finished(monkeypatch):
    """A game that used its last action will never act again even though its
    state still reads NOT_FINISHED, and both sweeps ended with games like it."""
    import broker

    monkeypatch.setattr(broker, "STATE", {"ls20": "GAME_OVER"})
    assert broker.spent("ls20")
    monkeypatch.setattr(broker, "STATE", {"ls20": "NOT_FINISHED"})
    assert not broker.spent("ls20")


def test_a_session_that_ended_early_does_not_hold_the_card_open(monkeypatch):
    """A session can stop with budget left: the game is neither WIN nor
    GAME_OVER, so state alone never marks it spent. One game like that would
    block the watchdog until the reaper took the card — which is the likeliest
    reason both 25-game sweeps lost their official scores."""
    import broker

    monkeypatch.setattr(broker, "STATE", {"ls20": "WIN", "quit_early": "NOT_FINISHED"})
    monkeypatch.setattr(broker, "DONE", set())
    games = ["ls20", "quit_early"]
    assert not broker.should_close(now=1e9, last_action=0, games=games, idle=600)

    # its session reports in, having ended — now nothing can act, so close.
    monkeypatch.setattr(broker, "DONE", {"quit_early"})
    assert broker.should_close(now=1e9, last_action=0, games=games, idle=600)


def test_the_idle_window_survives_an_empty_environment_variable(monkeypatch):
    """cloud.py passed the variable through as "" when it was not set, and
    int("") killed the broker on startup — a 25-game sweep failed to launch at
    all. Unset and empty have to mean the same thing."""
    import importlib

    import broker

    for value in ("", None):
        monkeypatch.delenv("ARCSEC_IDLE_CLOSE", raising=False)
        if value is not None:
            monkeypatch.setenv("ARCSEC_IDLE_CLOSE", value)
        assert importlib.reload(broker).IDLE_CLOSE == 600

    monkeypatch.setenv("ARCSEC_IDLE_CLOSE", "90")
    assert importlib.reload(broker).IDLE_CLOSE == 90
    monkeypatch.delenv("ARCSEC_IDLE_CLOSE")
    importlib.reload(broker)


def test_a_failed_close_stays_retryable(monkeypatch):
    """A 25-game pass lost its official score here. The card was marked closed before
    ARC had closed it, so when the close threw, the watchdog and a manual stop
    both reported success without retrying — and the card was reaped."""
    import broker

    class Card:
        card_id = "c1"

        def __init__(self):
            self.calls = 0

        def close(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("ARC said 500")
            return {"score": 95.0}

    card = Card()
    monkeypatch.setattr(broker, "CARD", [card])
    monkeypatch.setattr(broker, "CLOSED", [False])
    monkeypatch.setattr(broker, "RUN", "")

    with pytest.raises(RuntimeError):
        broker.close_card()
    assert not broker.CLOSED[0], "a close that threw must not count as closed"

    got = broker.close_card()  # the watchdog, ten minutes later
    assert got["closed"] and got["official"] == {"score": 95.0}
    assert broker.CLOSED[0] and card.calls == 2


def test_the_broker_never_authenticates_without_a_token(monkeypatch):
    """It fails CLOSED. This process holds the game key and listens on a public
    address, so an unset token used to authorise every request — an open proxy
    onto whoever ran it. A missing token now denies rather than allows."""
    import broker

    class Ask:
        def __init__(self, header):
            self.headers = {"Authorization": header} if header else {}
            self.denied = None

        def reply(self, code, body):
            self.denied = code

    monkeypatch.delenv("ARCSEC_TOKEN", raising=False)
    for header in (None, "", "Bearer ", "Bearer anything"):
        ask = Ask(header)
        assert broker.Handler.allowed(ask) is False, f"unset token let {header!r} through"
        assert ask.denied == 401

    monkeypatch.setenv("ARCSEC_TOKEN", "s3cret")
    assert broker.Handler.allowed(Ask("Bearer s3cret")) is True
    assert broker.Handler.allowed(Ask("Bearer wrong")) is False
    assert broker.Handler.allowed(Ask(None)) is False
