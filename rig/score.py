#!/usr/bin/env python3
"""ARC's score, computed here rather than remembered.

ARC only reveals a score when a scorecard is closed, and a card that goes
fifteen minutes without an action is reaped with its score. Two of my best runs
lost theirs that way. So the formula is reverse-engineered and kept in the
repository, where it can be re-run and tested, instead of in a notebook that
dies with the container — a headline nobody can recompute is not a result.

    uv run score.py verify              # against every score ARC has disclosed
    uv run score.py run sealed          # one run, per game and overall
    uv run score.py best sealed sealed2 # the better of two passes per game

The formula, fitted to ARC's own numbers and then checked against them:

    level_score = min(115, 100 * (human / ours) ** 2)   cleared levels
                = 0                                     levels never cleared
    game_score  = min(100, sum(i * level_score[i]) / sum(i))    i = 1..levels

Two things follow, and both shaped how the games were played. A level's weight
is its index, so the last level of a nine-level game is worth nine times the
first. And a full clear caps at 100, so being faster than the human baseline is
invisible while failing a late level is ruinous. Finishing dominates.
"""

import argparse
import json
from pathlib import Path

import db

REPO = Path(__file__).resolve().parent
BASELINES = REPO / "baselines.json"
EFFICIENCY_CAP = 115.0
GAME_CAP = 100.0


def baselines() -> dict[str, list[int]]:
    """How many actions a human needed on each level, per game.

    Extracted from ARC's own closed scorecards — each environment on a closed
    card reports `level_baseline_actions`. They are a property of the game
    rather than of a run: every card that discloses them for a game agrees, so
    the file is committed rather than re-fetched. Keyed by the four-character
    prefix, since the suffix differs per card.
    """
    found = json.loads(BASELINES.read_text())
    if not found:
        raise SystemExit(f"score: no baselines in {BASELINES}")
    return found


def level_score(ours: int, human: int) -> float:
    """One cleared level. Squared, so being twice as slow costs three quarters."""
    if ours <= 0:
        return 0.0
    return min(EFFICIENCY_CAP, 100.0 * (human / ours) ** 2)


def game_score(actions: list[int], human: list[int], cleared: int) -> float:
    """A game, from the actions each level took and how many were cleared.

    `actions` may be shorter than the game — levels never reached contribute
    nothing but still carry their weight in the denominator, which is what makes
    an unfinished game expensive.
    """
    total = sum(range(1, len(human) + 1))
    earned = sum(
        (i + 1) * level_score(actions[i], human[i]) for i in range(min(cleared, len(human)))
    )
    return min(GAME_CAP, earned / total) if total else 0.0


def levels_of(run: str) -> dict[str, tuple[list[int], int, str]]:
    """Per-level action counts for every game in a run, from the record.

    The opening RESET is an action here and is not one to ARC, so level one is
    always one longer in my table than in theirs. Measured on all five games
    of a Codex batch, where both numbers exist: every other level matches
    exactly.
    """
    rows = db.sql(
        "select a.game, a.level, count(*) n, max(g.state) state"
        " from actions a join games g on g.run = a.run and g.game = a.game"
        " where a.run = $1 group by a.game, a.level order by a.game, a.level",
        run,
    )
    games: dict[str, tuple[list[int], int, str]] = {}
    for row in rows:
        actions, _, _ = games.get(row["game"], ([], 0, ""))
        actions.append(int(row["n"]) - (1 if int(row["level"]) == 1 else 0))
        games[row["game"]] = (actions, 0, row["state"])
    # A level is cleared when a later one was reached, or when the game was won.
    return {
        game: (actions, len(actions) if state == "WIN" else len(actions) - 1, state)
        for game, (actions, _, state) in games.items()
    }


def stated(run: str) -> dict[str, float]:
    """What ARC said, for the games on a card it actually closed."""
    said = {}
    for row in official(run):
        for env in row["official"].get("environments", []):
            said[env["id"][:4]] = env["score"]
    return said


def scores(
    run: str, human: dict[str, list[int]] | None = None, reconstruct: bool = False
) -> dict[str, float]:
    """Each game's score: ARC's own number where there is one, mine otherwise.

    Reconstruction exists because a reaped card discloses nothing, not because
    it is better than the source. It agrees with ARC on 57 of the 60 games where
    both exist, and the three it misses are games with deaths in them — my
    `attempt` counter increments on GAME_OVER and resets each level, so it does
    not line up with the runs ARC records on a card, and no grouping of my
    record reproduces theirs. Where ARC has spoken, ARC wins.
    """
    human = human or baselines()
    said = {} if reconstruct else stated(run)
    out = {}
    for game, (actions, cleared, _) in levels_of(run).items():
        if game[:4] not in human:
            continue
        out[game[:4]] = said.get(game[:4], game_score(actions, human[game[:4]], cleared))
    return out


def official(run: str | None = None) -> list[dict]:
    where, params = ("and run = $1", [run]) if run else ("", [])
    return db.sql(
        f"select run, game, official from games where official is not null {where}"
        " order by run, game",
        *params,
    )


# One game disagrees, in both runs where ARC scored it, and it is left
# disagreeing rather than fitted around.
#
# `sk48` cleared five of eight levels and ARC reports every one of them at the
# 115 cap — yet its total, 41.67, is exactly 100 * 15/36, which is what those
# levels scoring 100 would give. Two other unfinished games, `ls20` and `wa30`,
# reproduce to twelve decimal places only if the 115s are taken at face value.
# So the four unfinished games ARC has scored here do not agree with each
# other, and no single rule fits all four.
#
# An earlier scorer, since lost, used progress alone for unfinished games. That
# rule fits `sk48` and misses `ls20` and `wa30` by twenty points. This one fits
# those two and misses `sk48` by six. It is the better of the two and it is not
# right, which is worth saying plainly: an unfinished game's score is uncertain
# by a few points. Finished games are exact, and every headline below rests on
# games that were finished.
# `g50t` is a different failure and it is understood: the game died and was
# retried, ARC recorded two runs on the card, and my record cannot say where
# their boundary fell. `attempt` in the actions table increments on GAME_OVER
# and resets on each new level, so it counts deaths per level, not sessions.
# Grouping by it and taking the best was tried and made four other games worse.
# Reconstruction is therefore unreliable for games containing a death, by up to
# the 36 points seen here.
UNEXPLAINED = {("sweep1", "sk48"), ("sweep1-again", "sk48"), ("codex-hard5", "g50t")}


def verify(args: argparse.Namespace) -> None:
    """Recompute every score ARC has ever disclosed, from my own record.

    Not a re-reading of ARC's answer: the per-level actions come from my
    `actions` table and only the human baselines from ARC's disclosures, so a
    match means the whole path — reconstruction and formula — is right.
    """
    human, checked, wrong = baselines(), 0, []
    for run in sorted({row["run"] for row in official()}):
        mine, theirs = scores(run, human, reconstruct=True), stated(run)
        for game, want in sorted(theirs.items()):
            if game not in mine:
                continue
            checked += 1
            if abs(mine[game] - want) > 0.05:
                wrong.append((run, game, mine[game], want))
    print(f"{checked - len(wrong)}/{checked} scores reproduced from my own record")
    for run, game, got, want in wrong:
        known = " (known, see UNEXPLAINED)" if (run, game) in UNEXPLAINED else ""
        print(f"  {run:14} {game}  computed {got:6.2f}  ARC said {want:6.2f}{known}")
    if [w for w in wrong if (w[0], w[1]) not in UNEXPLAINED]:
        raise SystemExit("score: a new game stopped reproducing — the formula moved")


def show(args: argparse.Namespace) -> None:
    table = scores(args.run)
    if not table:
        raise SystemExit(f"score: nothing recorded for {args.run}")
    for game, value in sorted(table.items()):
        print(f"  {game}  {value:6.2f}")
    print(f"\n{args.run}: {sum(table.values()) / len(table):.1f} over {len(table)} games")


def best(args: argparse.Namespace) -> None:
    """The better of several passes per game."""
    human = baselines()
    passes = {run: scores(run, human) for run in args.runs}
    games = sorted(set().union(*(set(p) for p in passes.values())))
    for game in games:
        each = [passes[run].get(game) for run in args.runs]
        got = [v for v in each if v is not None]
        cells = "  ".join(f"{v:6.2f}" if v is not None else "     —" for v in each)
        print(f"  {game}  {cells}   -> {max(got):6.2f}")
    overall = [max(v for v in (p.get(g) for p in passes.values()) if v is not None) for g in games]
    for run in args.runs:
        single = passes[run]
        print(f"\n{run:16} {sum(single.values()) / len(single):.1f} over {len(single)} games")
    print(f"{'best@' + str(len(args.runs)):16} {sum(overall) / len(overall):.1f} over {len(games)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="score", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify", help="check the formula against every official score").set_defaults(
        func=verify
    )
    one = sub.add_parser("run", help="score one run")
    one.add_argument("run")
    one.set_defaults(func=show)
    pair = sub.add_parser("best", help="best of several passes, per game")
    pair.add_argument("runs", nargs="+")
    pair.set_defaults(func=best)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
