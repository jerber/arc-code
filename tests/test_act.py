"""Tests for the actuator.

The important property is fidelity: the log is the agent's memory and the
scorer's source, so its layout is pinned here byte for byte. Every test drives
a scripted game so the exact sequence of scores and states can be chosen.
"""

import re
from pathlib import Path

import pytest

import act
from act import ActError, Obs, RunState, Step


def test_playing_again_keeps_the_memory_and_clears_only_the_game(tmp_path):
    """A dead scorecard means the game restarts, not the workspace. The last
    attempt's log is kept beside the new one rather than appended to: action
    numbering starts over, and two runs interleaved in one file parse as
    neither."""
    (tmp_path / act.LOG).write_text("first attempt")
    (tmp_path / act.STATE).write_text("{}")
    (tmp_path / "notes.md").write_text("what I learned")
    (tmp_path / "solve.py").write_text("print(1)")

    act.restart(tmp_path)

    assert not (tmp_path / act.STATE).exists(), "the game is cleared"
    assert not (tmp_path / act.LOG).exists(), "the new attempt starts a fresh log"
    assert (tmp_path / "logs-attempt1.txt").read_text() == "first attempt"
    assert (tmp_path / "notes.md").read_text() == "what I learned", "memory survives"
    assert (tmp_path / "solve.py").exists(), "so do the tools it built"


def test_a_third_attempt_does_not_overwrite_the_second(tmp_path):
    for expected in ("logs-attempt1.txt", "logs-attempt2.txt"):
        (tmp_path / act.LOG).write_text(expected)
        (tmp_path / act.STATE).write_text("{}")
        act.restart(tmp_path)
        assert (tmp_path / expected).read_text() == expected


BLANK = [[0] * 64 for _ in range(64)]


class ScriptedGame:
    """A game whose every response is decided in advance."""

    def __init__(self, responses: list[tuple[str, int]], layers: int = 1) -> None:
        self.responses = responses
        self.layers = layers
        self.played: list[Step] = []

    def _obs(self, state: str, score: int) -> Obs:
        return Obs(
            state=state,
            score=score,
            win_levels=6,
            guid="g",
            available_actions=["ACTION1", "ACTION6", "RESET"],
            layers=[BLANK] * self.layers,
        )

    def reset(self) -> Obs:
        return self._obs("NOT_FINISHED", 0)

    def step(self, step: Step) -> Obs:
        self.played.append(step)
        return self._obs(*self.responses[len(self.played) - 1])


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A workspace with a game already initialised."""
    monkeypatch.chdir(tmp_path)
    state = RunState(game_id="test-0000")
    game = ScriptedGame([])
    obs = game.reset()
    act.apply_observation(state, obs)
    act.log_initial(tmp_path, state, obs.layers)
    state.save(tmp_path)
    return tmp_path


def play(ws: Path, tokens: list[str], responses, plan=None, layers=1) -> ScriptedGame:
    game = ScriptedGame(responses, layers=layers)
    args = type("Args", (), {"actions": tokens, "plan": plan, "board": False})()
    act.open_game = lambda _state: game  # noqa: ARG005
    act.cmd_do(args, ws)
    return game


@pytest.fixture(autouse=True)
def _restore_open_game():
    original = act.open_game
    yield
    act.open_game = original


# --- rendering fidelity ---------------------------------------------------- #


def test_grids_render_as_hex_digits():
    # The character is the value — no legend needed to parse, int(c, 16) suffices.
    assert act.format_grid([[5, 9, 8, 0]]) == "5980"
    assert act.format_grid([[12, 11, 14, 15]]) == "cbef"
    assert act.format_grid([[99, -3]]) == "f0"  # clamped, never crashes


def test_the_log_documents_itself(ws):
    # The format and the color legend live in the log, not in the prompt.
    ours = (ws / "logs.txt").read_text()
    assert ours.startswith("# logs.txt")
    assert "0=White" in ours and "f=Purple" in ours
    assert "[final]" in act.PREAMBLE and "[anim" in act.PREAMBLE


def test_initial_block_layout(ws):
    ours = (ws / "logs.txt").read_text()
    body = ours.partition("=" * 80)[2]
    lines = body.splitlines()
    assert lines[1] == "action 0 | level 1 attempt 1 | score 0 | start"
    assert lines[2] == ""
    assert lines[3] == "[board]"
    assert ours.endswith("\n\n")


def test_action_block_layout(ws):
    play(ws, ["ACTION6:30,40"], [("NOT_FINISHED", 0)], plan="probe the corner")
    block = (ws / "logs.txt").read_text().split("=" * 80)[-1]
    assert block == (
        "\naction 1 | level 1 attempt 1 | score 0 | ACTION6 x=30 y=40 | step 1/1\n\n"
        "plan: probe the corner\n\n"
        "[board]\n" + act.format_grid(BLANK) + "\n\n"
    )


def test_animation_frames_are_rendered(ws):
    play(ws, ["ACTION1"], [("NOT_FINISHED", 0)], layers=3)
    text = (ws / "logs.txt").read_text()
    assert "[anim 1/2]" in text and "[anim 2/2]" in text and "[final]" in text


# --- batch semantics ------------------------------------------------------- #


def test_scoring_action_ends_the_batch_and_drops_its_label(ws):
    game = play(ws, ["ACTION1"] * 5, [("NOT_FINISHED", 0), ("NOT_FINISHED", 1)])
    assert len(game.played) == 2, "should stop on the action that scored"
    headers = [ln for ln in (ws / "logs.txt").read_text().splitlines() if ln.startswith("action ")]
    assert headers[1].endswith("ACTION1 | step 1/5")
    assert headers[2] == "action 2 | level 1 attempt 1 | score 1 | ACTION1", (
        "label dropped when cut short"
    )


def test_label_survives_when_the_last_action_scores(ws):
    play(ws, ["ACTION1", "ACTION1"], [("NOT_FINISHED", 0), ("NOT_FINISHED", 1)])
    headers = [ln for ln in (ws / "logs.txt").read_text().splitlines() if ln.startswith("action ")]
    assert headers[2] == "action 2 | level 1 attempt 1 | score 1 | ACTION1 | step 2/2"


def test_level_increments_after_the_scoring_action_is_logged(ws):
    play(ws, ["ACTION1"], [("NOT_FINISHED", 1)])
    assert RunState.load(ws).level == 2
    play(ws, ["ACTION1"], [("NOT_FINISHED", 1)])
    headers = [ln for ln in (ws / "logs.txt").read_text().splitlines() if ln.startswith("action ")]
    assert "level 1" in headers[1], "the scoring action belongs to the level it cleared"
    assert "level 2" in headers[2], "the next action is on the new level"


def test_plan_persists_until_replaced(ws):
    play(ws, ["ACTION1"], [("NOT_FINISHED", 0)], plan="first")
    play(ws, ["ACTION1"], [("NOT_FINISHED", 0)])
    play(ws, ["ACTION1"], [("NOT_FINISHED", 0)], plan="second")
    plans = re.findall(r"plan: (.+)", (ws / "logs.txt").read_text())
    assert plans == ["first", "first", "second"]


def test_game_over_ends_the_batch_and_bumps_the_attempt(ws):
    game = play(ws, ["ACTION1"] * 3, [("NOT_FINISHED", 0), ("GAME_OVER", 0)])
    assert len(game.played) == 2
    assert RunState.load(ws).attempt == 2


# --- guards: every one of these must fail loudly --------------------------- #


@pytest.mark.parametrize(
    ("tokens", "message"),
    [
        (["ACTION9"], "not available"),
        (["ACTION6"], "needs coordinates"),
        (["ACTION6:64,0"], "outside the 64x64 board"),
        (["ACTION6:x,y"], "could not read coordinates"),
        (["ACTION1:3,4"], "takes no coordinates"),
        (["RESET", "RESET"], "two RESETs in a row"),
    ],
)
def test_bad_input_raises(ws, tokens, message):
    with pytest.raises(ActError, match=message):
        play(ws, tokens, [("NOT_FINISHED", 0)] * 4)


def test_batch_larger_than_the_budget_is_refused_before_acting(ws):
    state = RunState.load(ws)
    state.max_actions = 2
    state.save(ws)
    with pytest.raises(ActError, match="only 2 left"):
        play(ws, ["ACTION1"] * 3, [("NOT_FINISHED", 0)] * 3)
    assert RunState.load(ws).actions_used == 0, "nothing may run when the batch is refused"


def test_playing_on_after_a_win_is_refused(ws):
    play(ws, ["ACTION1"], [("WIN", 6)])
    with pytest.raises(ActError, match="already won"):
        play(ws, ["ACTION1"], [("WIN", 6)])


def test_game_over_requires_reset_first(ws):
    play(ws, ["ACTION1"], [("GAME_OVER", 0)])
    with pytest.raises(ActError, match="must be RESET"):
        play(ws, ["ACTION1"], [("NOT_FINISHED", 0)])


def test_missing_state_file_raises(tmp_path):
    with pytest.raises(ActError, match="run `act init"):
        RunState.load(tmp_path)
