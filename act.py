#!/usr/bin/env python3
"""Deterministic actuator for ARC-AGI-3.

Every action goes through here, and every action is appended verbatim to
``logs.txt`` together with the board it produced. That log is the agent's
memory: written by code, read by code. The agent supplies judgement; this file
supplies side effects, bookkeeping and an honest record.

Nothing here degrades gracefully. If something is wrong, it raises.
"""

import argparse
import os
import sys
import time
from itertools import count
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from pydantic import BaseModel
from requests.utils import dict_from_cookiejar

BASE_URL = "https://three.arcprize.org"

LOG = "logs.txt"
STATE = "state.json"
SCORECARD = "scorecard.json"

SEP = "=" * 80
COORD_ACTION = "ACTION6"
RESET = "RESET"

RETRY_DELAYS = (1, 2, 4, 8, 16)  # for the transient failures only: limits and networks

# Room to finish rather than a target: the hardest published runs of these games
# take well over a thousand actions, and a run cut short teaches nothing.
DEFAULT_BUDGET = 2500


class ActError(SystemExit):
    """Loud, non-zero exit. The message is the agent's feedback channel."""

    def __init__(self, message: str) -> None:
        super().__init__(f"act: {message}")


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #


class Step(BaseModel):
    name: str
    x: int | None = None
    y: int | None = None

    def __str__(self) -> str:
        return f"{self.name}({self.x},{self.y})" if self.name == COORD_ACTION else self.name


class Obs(BaseModel):
    """One observation, as the game API reports it."""

    state: str
    score: int
    win_levels: int
    guid: str | None
    available_actions: list[str]
    layers: list[list[list[int]]]


class RunState(BaseModel):
    game_id: str
    max_actions: int = DEFAULT_BUDGET
    scorecard_id: str | None = None
    guid: str | None = None
    cookies: dict[str, str] = {}
    actions_used: int = 0
    score: int = 0
    max_score: int = 0
    win_levels: int = 0
    level: int = 1
    attempt: int = 1
    state: str = "NOT_PLAYED"
    last_action: str | None = None
    plan: str | None = None
    available_actions: list[str] = []
    history: list[Step] = []
    last_grid: list[list[int]] | None = None

    @classmethod
    def load(cls, ws: Path) -> "RunState":
        path = ws / STATE
        if not path.exists():
            raise ActError(f"no {STATE} in {ws} — run `act init <game>` first")
        return cls.model_validate_json(path.read_text())

    def save(self, ws: Path) -> None:
        tmp = ws / f"{STATE}.tmp"
        tmp.write_text(self.model_dump_json(indent=2))
        tmp.replace(ws / STATE)

    @property
    def actions_left(self) -> int:
        return self.max_actions - self.actions_used


# --------------------------------------------------------------------------- #
# Rendering — the log format every parser downstream depends on
# --------------------------------------------------------------------------- #


def format_grid(grid: list[list[int]]) -> str:
    """Render a grid as hex digits, one per cell — the character *is* the value."""
    return "\n".join(
        "".join(format(max(0, min(15, int(v))), "x") for v in row) for row in grid
    )


def render_frames(layers: list[list[list[int]]]) -> str:
    """Render the final board, preceded by animation frames when present."""
    if not layers:
        raise ActError("environment returned no frame")
    if len(layers) == 1:
        return format_grid(layers[0])
    parts = []
    for i, layer in enumerate(layers[:-1], start=1):
        parts.append(f"[anim {i}/{len(layers) - 1}]")
        parts.append(format_grid(layer))
    parts.append("[final]")
    parts.append(format_grid(layers[-1]))
    return "\n".join(parts)


# The log explains itself, so the prompt does not have to.
PREAMBLE = (
    "# logs.txt — the complete record of this run, written by the actuator.\n"
    "# One block per action: a ruler of = signs, then\n"
    "#   action N | level L attempt A | score S | <what was played> | step i/k\n"
    "# then the plan that batch was given, then [board] — the state it\n"
    "# produced, rows of hex digits, one cell each, value 0-15.\n"
    "# An action that animates logs [anim i/N] frames first; the grid after\n"
    "# [final] is what committed.\n"
    "# colors: 0=White 1=Off-White 2=Light-Gray 3=Gray 4=Off-Black 5=Black\n"
    "#         6=Magenta 7=Light-Magenta 8=Red 9=Blue a=Light-Blue b=Yellow\n"
    "#         c=Orange d=Maroon e=Green f=Purple\n"
)


def log_initial(ws: Path, state: RunState, layers: list[list[list[int]]]) -> None:
    block = (
        f"{PREAMBLE}{SEP}\n"
        f"action 0 | level {state.level} attempt {state.attempt} | "
        f"score {state.score} | start\n\n"
        f"[board]\n{render_frames(layers)}\n\n"
    )
    (ws / LOG).write_text(block)


def log_action(
    ws: Path,
    state: RunState,
    step: Step,
    layers: list[list[list[int]]],
    plan_index: int,
    plan_total: int,
) -> None:
    """Append one action block. Called after the action count and score update,
    but before level/attempt bookkeeping — so the header carries the new score
    alongside the level the action was played on."""
    label = f" | step {plan_index}/{plan_total}" if plan_total else ""
    played = (
        f"{step.name} x={step.x} y={step.y}" if step.name == COORD_ACTION else step.name
    )
    block = (
        f"\n{SEP}\n"
        f"action {state.actions_used} | level {state.level} attempt {state.attempt} | "
        f"score {state.score} | {played}{label}\n\n"
        + (f"plan: {state.plan}\n\n" if state.plan else "")
        + f"[board]\n{render_frames(layers)}\n\n"
    )
    with (ws / LOG).open("a") as f:
        f.write(block)


# --------------------------------------------------------------------------- #
# The game
# --------------------------------------------------------------------------- #


def action_names(codes: list[int]) -> list[str]:
    return sorted({f"ACTION{c}" for c in codes} | {RESET})


class OnlineGame:
    """The ARC-AGI-3 HTTP API.

    Speaks the protocol directly rather than through the toolkit, whose
    ``make()`` resets the game on construction — which would restart the run on
    every invocation. Holding the guid ourselves is what makes the agent's
    session survive across calls.
    """

    def __init__(self, state: RunState) -> None:
        self.game_id = state.game_id
        self.card_id = state.scorecard_id
        self.guid = state.guid
        self._session = api_session(state.cookies)

    @property
    def cookies(self) -> dict[str, str]:
        return dict_from_cookiejar(self._session.cookies)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST, retrying only what is worth retrying.

        Rate limits and server faults pass; a 4xx means the request asked for something
        impossible and asking again will not help.
        """
        for delay in (*RETRY_DELAYS, None):
            try:
                r = self._session.post(f"{BASE_URL}{path}", json=payload, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as exc:
                if delay is None:
                    raise ActError(f"POST {path} unreachable after retries: {exc}") from exc
                time.sleep(delay)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                if delay is None:
                    raise ActError(
                        f"POST {path} still {r.status_code} after retries: {r.text[:300]}"
                    )
                time.sleep(delay)
                continue
            if not r.ok:
                raise ActError(f"POST {path} -> {r.status_code}: {r.text[:300]}")
            return r.json()
        raise AssertionError("unreachable")

    def _obs(self, payload: dict[str, Any]) -> Obs:
        from arcengine import FrameData

        frame = FrameData.model_validate(payload)
        self.guid = frame.guid
        return Obs(
            state=frame.state.name,
            score=frame.levels_completed,
            win_levels=frame.win_levels,
            guid=frame.guid,
            available_actions=action_names(frame.available_actions),
            layers=[[list(row) for row in layer] for layer in frame.frame],
        )

    def reset(self) -> Obs:
        body: dict[str, Any] = {"game_id": self.game_id, "card_id": self.card_id}
        if self.guid:
            body["guid"] = self.guid
        return self._obs(self._post("/api/cmd/RESET", body))

    def step(self, step: Step) -> Obs:
        if step.name == RESET:
            return self.reset()
        body: dict[str, Any] = {"game_id": self.game_id, "guid": self.guid}
        if step.name == COORD_ACTION:
            body |= {"x": step.x, "y": step.y}
        return self._obs(self._post(f"/api/cmd/{step.name}", body))


def open_game(state: RunState) -> OnlineGame:
    """Return a live game positioned exactly where the state left off."""
    return OnlineGame(state)


def api_session(cookies: dict[str, str] | None = None) -> requests.Session:
    key = os.environ.get("ARC_API_KEY")
    if not key:
        raise ActError("ARC_API_KEY is not set — required to play")
    session = requests.Session()
    session.headers.update({"X-API-Key": key, "Accept": "application/json"})
    # Restore with the server's own domain, so its Set-Cookie replaces these
    # rather than sitting beside them as a duplicate.
    for name, value in (cookies or {}).items():
        session.cookies.set(name, value, domain=urlparse(BASE_URL).hostname, path="/")
    return session


class Scorecard(BaseModel):
    """A scorecard and the cookies that reach it.

    Opening one pins the session to a particular server, and commands sent
    without those cookies are rejected with "game not found" — so the two
    always travel together.
    """

    card_id: str
    cookies: dict[str, str]

    @classmethod
    def open(cls, tags: list[str]) -> "Scorecard":
        session = api_session()
        r = session.post(f"{BASE_URL}/api/scorecard/open", json={"tags": tags}, timeout=30)
        if not r.ok:
            raise ActError(f"could not open a scorecard -> {r.status_code}: {r.text[:300]}")
        return cls(card_id=r.json()["card_id"], cookies=dict_from_cookiejar(session.cookies))

    @classmethod
    def load(cls, ws: Path) -> "Scorecard | None":
        path = ws / SCORECARD
        return cls.model_validate_json(path.read_text()) if path.exists() else None

    def save(self, ws: Path) -> None:
        (ws / SCORECARD).write_text(self.model_dump_json(indent=2))

    def alive(self) -> bool:
        """Whether ARC still answers for this card.

        A card is dropped once it is closed, and reaped after fifteen minutes
        idle — taking its game sessions with it. Playing on either is the
        `game not found` that killed every resumed game in an earlier batch.
        """
        r = api_session(self.cookies).get(
            f"{BASE_URL}/api/scorecard/{self.card_id}", timeout=30
        )
        return r.ok

    def close(self) -> dict[str, Any]:
        """Close the card and return ARC's own scoring of the run.

        This is the only way to get the official per-level scores, and it has to
        happen while the session that opened the card is still alive — once the
        card goes idle the API no longer answers for it, and the numbers are
        gone.
        """
        session = api_session(self.cookies)
        r = session.post(
            f"{BASE_URL}/api/scorecard/close", json={"card_id": self.card_id}, timeout=30
        )
        if not r.ok:
            raise ActError(
                f"could not close scorecard {self.card_id} -> {r.status_code}: {r.text[:300]}"
            )
        return r.json()


# --------------------------------------------------------------------------- #
# Parsing and bookkeeping
# --------------------------------------------------------------------------- #


def parse_actions(tokens: list[str], available: list[str]) -> list[Step]:
    """``ACTION1``  ``ACTION6:30,40``  ``RESET`` — anything else is an error."""
    steps = []
    for token in tokens:
        name, _, coords = token.upper().partition(":")
        if name not in available:
            raise ActError(f"{name!r} is not available in this game — choose from {available}")
        if name == COORD_ACTION:
            if not coords:
                raise ActError(f"{COORD_ACTION} needs coordinates, e.g. {COORD_ACTION}:30,40")
            try:
                x_raw, y_raw = coords.split(",")
                x, y = int(x_raw), int(y_raw)
            except ValueError:
                raise ActError(f"could not read coordinates from {token!r} — want x,y") from None
            if not (0 <= x <= 63 and 0 <= y <= 63):
                raise ActError(f"coordinates ({x},{y}) are outside the 64x64 board")
            steps.append(Step(name=name, x=x, y=y))
        else:
            if coords:
                raise ActError(f"{name} takes no coordinates, got {token!r}")
            steps.append(Step(name=name))
    if not steps:
        raise ActError("no actions given")
    return steps


def apply_observation(state: RunState, obs: Obs) -> bool:
    """Fold an observation into the run state. Returns True if the score moved.

    Level and attempt are not reported by the environment: a level is cleared
    when the score reaches a new high, and an attempt ends when the game does.
    """
    previous_score, previous_state = state.score, state.state
    state.score = obs.score
    state.state = obs.state
    state.win_levels = obs.win_levels
    state.guid = obs.guid
    state.available_actions = obs.available_actions
    state.last_grid = obs.layers[-1]
    return state.score != previous_score or state.state != previous_state


def advance_level(state: RunState) -> None:
    """Bookkeeping that must happen *after* the action is logged."""
    if state.score > state.max_score and state.state not in ("WIN", "GAME_OVER"):
        state.max_score = state.score
        state.level += 1
        state.attempt = 1
    else:
        state.max_score = max(state.max_score, state.score)
        if state.state == "GAME_OVER":
            state.attempt += 1


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def restart(ws: Path) -> None:
    """Clear a workspace's *game* while leaving its memory alone.

    A dead scorecard takes its session with it, so carrying on means playing
    the game again from level one. What the last attempt learned need not go
    with it: notes and helper scripts stay put, and its log is kept beside the
    new one rather than appended to, because action numbering restarts and two
    runs interleaved in one file would parse as neither.
    """
    log = ws / LOG
    if log.exists():
        taken = (ws / f"logs-attempt{n}.txt" for n in count(1))
        log.rename(next(path for path in taken if not path.exists()))
    (ws / STATE).unlink()


def cmd_init(args: argparse.Namespace, ws: Path) -> None:
    if (ws / STATE).exists():
        if not args.again:
            raise ActError(f"{ws} is already initialised — use a fresh directory")
        restart(ws)

    # A scorecard placed here by the launcher is one several games share;
    # otherwise this workspace opens its own and records it.
    card = Scorecard.load(ws)
    if card is None:
        card = Scorecard.open(tags=["arc-code"])
        card.save(ws)

    state = RunState(
        game_id=args.game,
        max_actions=args.max_actions,
        scorecard_id=card.card_id,
        cookies=card.cookies,
    )
    game = OnlineGame(state)
    obs = game.reset()
    apply_observation(state, obs)
    state.cookies = game.cookies

    log_initial(ws, state, obs.layers)
    state.save(ws)

    print(f"{args.game} ready — {state.win_levels} levels, {state.max_actions} actions")
    print(f"actions: {' '.join(state.available_actions)}")
    print(f"board: {LOG} (Action 0)")


def cmd_do(args: argparse.Namespace, ws: Path) -> None:
    state = RunState.load(ws)
    if args.plan:
        state.plan = args.plan

    if state.state == "WIN":
        raise ActError("this game is already won — nothing left to play")
    steps = parse_actions(args.actions, state.available_actions)
    if state.state == "GAME_OVER" and steps[0].name != RESET:
        raise ActError("the game is over — the next action must be RESET")
    # Back-to-back RESETs restart the whole game instead of the level.
    previous = state.last_action
    for step in steps:
        if step.name == RESET and previous == RESET:
            raise ActError("two RESETs in a row would restart the game, not the level")
        previous = step.name
    if len(steps) > state.actions_left:
        raise ActError(
            f"{len(steps)} actions requested but only {state.actions_left} left in the budget"
        )

    game = open_game(state)
    total = len(steps)
    done: list[Step] = []
    flushed: str | None = None

    for index, step in enumerate(steps, start=1):
        obs = game.step(step)
        state.actions_used += 1
        state.last_action = step.name
        state.history.append(step)
        done.append(step)

        before = state.score
        changed = apply_observation(state, obs)
        scored = state.score != before
        remaining = total - index
        # A score change ends the batch: the board the agent planned against no
        # longer exists. The label is dropped when a plan is cut short so the
        # log shows the sequence was abandoned.
        log_action(
            ws,
            state,
            step,
            obs.layers,
            0 if scored and remaining else index,
            0 if scored and remaining else total,
        )
        advance_level(state)
        if isinstance(game, OnlineGame):
            state.cookies = game.cookies
        state.save(ws)

        if scored:
            flushed = f"score {before} -> {state.score}"
            if remaining:
                flushed += f", {remaining} action(s) dropped"
            break
        if changed and state.state in ("WIN", "GAME_OVER"):
            flushed = f"state {state.state}"
            if remaining:
                flushed += f", {remaining} action(s) dropped"
            break

    print(f"ran {len(done)}/{total}: {' '.join(str(s) for s in done)}")
    if flushed:
        print(f"stopped early: {flushed}")
    print(
        f"score={state.score} level={state.level} attempt={state.attempt} "
        f"state={state.state} actions={state.actions_used}/{state.max_actions}"
    )
    print(f"boards: {LOG} (through Action {state.actions_used})")
    if args.board and state.last_grid:
        print(format_grid(state.last_grid))


def cmd_status(_: argparse.Namespace, ws: Path) -> None:
    state = RunState.load(ws)
    print(
        f"{state.game_id} score={state.score}/{state.win_levels} "
        f"level={state.level} attempt={state.attempt} state={state.state} "
        f"actions={state.actions_used}/{state.max_actions}"
    )


def cmd_board(_: argparse.Namespace, ws: Path) -> None:
    state = RunState.load(ws)
    if state.last_grid is None:
        raise ActError("no board recorded yet")
    print(format_grid(state.last_grid))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="act", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="start a game in this directory")
    p_init.add_argument("game", help="game id, e.g. ft09-0d8bbf25")
    p_init.add_argument("--max-actions", type=int, default=DEFAULT_BUDGET, help="action budget")
    p_init.add_argument(
        "--again",
        action="store_true",
        help="play this game again in a workspace that already holds one, keeping its notes",
    )
    p_init.set_defaults(func=cmd_init)

    p_do = sub.add_parser("do", help="play actions, in order, until one scores")
    p_do.add_argument("actions", nargs="+", metavar="ACTION", help="e.g. ACTION1 ACTION6:30,40")
    p_do.add_argument("--plan", help="briefing recorded in the log beside these actions")
    p_do.add_argument("--board", action="store_true", help="also print the final board")
    p_do.set_defaults(func=cmd_do)

    sub.add_parser("status", help="one-line summary").set_defaults(func=cmd_status)
    sub.add_parser("board", help="print the current board").set_defaults(func=cmd_board)

    args = parser.parse_args(argv)
    args.func(args, Path.cwd())


if __name__ == "__main__":
    sys.exit(main())
