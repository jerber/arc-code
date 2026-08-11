"""Tests for the launcher: the environment handed to a session, and resuming."""

import json
from pathlib import Path

from run import child_env, unfinished


def test_child_env_strips_this_session_and_sets_the_key(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.setenv("CLAUDECODE", "1")
    env = child_env("sk-test")
    assert env["ANTHROPIC_API_KEY"] == "sk-test"
    assert "ANT_API_KEY" not in env
    assert "CLAUDE_CODE_ENTRYPOINT" not in env and "CLAUDECODE" not in env
    # The one CLAUDE_CODE_ variable the harness sets rather than inherits.
    assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"


def test_a_codex_session_gets_no_null_anthropic_key(monkeypatch):
    """Codex brings its own credential and there is no Anthropic key to hand it.
    Setting the variable to None anyway put a null in the environment, and every
    session in a brokered batch died before it started."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    env = child_env(None)
    assert "ANTHROPIC_API_KEY" not in env
    assert env["OPENAI_API_KEY"] == "sk-openai", "its own key passes through"
    assert all(v is not None for v in env.values())


def test_the_agent_is_not_given_the_record(monkeypatch):
    """The harness writes the run to Postgres; the agent has no use for the DSN,
    and that record contains previous winning runs of the game it is playing."""
    monkeypatch.setenv("POSTGRES_DSN", "postgres://u:p@ep-x.neon.tech/db")
    assert "POSTGRES_DSN" not in child_env("sk-test")


def workspace(tmp_path: Path, game: str, **state) -> Path:
    ws = tmp_path / game
    ws.mkdir()
    (ws / "state.json").write_text(
        json.dumps({"state": "NOT_FINISHED", "actions_used": 10, "max_actions": 2500, **state})
    )
    return tmp_path


def test_unfinished_finds_games_still_worth_playing(tmp_path):
    workspace(tmp_path, "playing")
    workspace(tmp_path, "won", state="WIN")
    workspace(tmp_path, "spent", actions_used=2500)
    games, card = unfinished(tmp_path)
    assert games == ["playing"]
    assert card is None


def test_a_brokered_workspace_is_resumable_without_local_state(tmp_path):
    """With a broker there is no state.json on the agent's side — the broker
    owns the game. The act shim is what marks the directory as a workspace;
    a directory without one is not a game at all."""
    brokered = tmp_path / "tn36-ef4dde99"
    brokered.mkdir()
    (brokered / "act").write_text("#!/bin/sh\n")
    (tmp_path / "not-a-workspace").mkdir()
    games, card = unfinished(tmp_path)
    assert games == ["tn36-ef4dde99"]
    assert card is None


def test_resuming_recovers_the_scorecard_the_games_started_on(tmp_path):
    """The unfinished games have to keep playing onto the card they opened —
    a fresh card would be a fresh run of every game."""
    workspace(tmp_path, "bp35", scorecard_id="card-1", cookies={"GAMESESSION": "x"})

    games, card = unfinished(tmp_path)
    assert games == ["bp35"] and card is not None and card.card_id == "card-1"
    assert card.cookies == {"GAMESESSION": "x"}, "the cookies that reach the card travel with it"


def test_the_reasoning_effort_can_be_set_for_a_batch(monkeypatch):
    """Effort belongs to a run, not a game, so it travels in the environment.
    xhigh costs enough that it has to be asked for rather than defaulted to."""
    import importlib

    import agents

    monkeypatch.setenv("ARCSEC_EFFORT", "xhigh")
    reloaded = importlib.reload(agents)
    assert reloaded.AGENTS["codex"].EFFORT == "xhigh"
    argv = reloaded.AGENTS["codex"].argv("play", "gpt-5.6-sol", Path("/tmp"))
    assert "model_reasoning_effort=xhigh" in argv

    monkeypatch.delenv("ARCSEC_EFFORT")
    assert importlib.reload(agents).AGENTS["codex"].EFFORT == "high", "default stays high"


def test_claude_takes_an_effort_level_and_defaults_to_the_cli_s_own(monkeypatch):
    """Every published pass ran at Claude Code's default, `high` for Opus 5,
    because nothing passed --effort at all. Leaving it unset must stay the
    default so those runs remain reproducible."""
    import importlib

    import agents

    monkeypatch.delenv("ARCSEC_EFFORT", raising=False)
    plain = importlib.reload(agents).AGENTS["claude"].argv("play", "claude-opus-5", Path("/tmp"))
    assert "--effort" not in plain, "unset must mean the CLI's own default"

    monkeypatch.setenv("ARCSEC_EFFORT", "max")
    deep = importlib.reload(agents).AGENTS["claude"].argv("play", "claude-opus-5", Path("/tmp"))
    assert deep[deep.index("--effort") + 1] == "max"

    monkeypatch.delenv("ARCSEC_EFFORT")
    importlib.reload(agents)


def test_codex_takes_the_effort_it_was_given(monkeypatch):
    """This rewrote `max` to `xhigh` on the belief that Codex had nothing above
    xhigh. It has `max` and `ultra`, so the rewrite was silently capping a batch
    that had asked to think harder."""
    import importlib

    import agents

    monkeypatch.setenv("ARCSEC_EFFORT", "max")
    assert importlib.reload(agents).AGENTS["codex"].EFFORT == "max"
    monkeypatch.delenv("ARCSEC_EFFORT")
    importlib.reload(agents)


def test_an_unknown_effort_stops_the_run_rather_than_being_ignored(monkeypatch):
    import importlib

    import agents
    import pytest as _pytest

    monkeypatch.setenv("ARCSEC_EFFORT", "ludicrous")
    reloaded = importlib.reload(agents)
    with _pytest.raises(SystemExit):
        reloaded.AGENTS["claude"].argv("play", "claude-opus-5", Path("/tmp"))
    monkeypatch.delenv("ARCSEC_EFFORT")
    importlib.reload(agents)
