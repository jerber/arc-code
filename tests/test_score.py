"""Tests for the score.

The headline number of this project is computed, not reported: ARC discloses a
score only when a card is closed, and two of the best runs lost theirs to the
reaper. So the formula has to be pinned against cases where ARC did answer,
using ARC's own published arithmetic rather than a memory of it.

The numbers below are taken verbatim from scorecards in the database.
"""



from score import EFFICIENCY_CAP, GAME_CAP, game_score, level_score


def test_a_level_scores_on_the_square_of_the_ratio():
    """From r11l, where ARC published both the actions and the level score."""
    assert level_score(53, 51) == 100.0 * (51 / 53) ** 2  # ARC: 92.59522961908152
    assert round(level_score(53, 51), 10) == 92.5952296191
    assert round(level_score(30, 26), 10) == 75.1111111111  # ARC: 75.11111111111111


def test_beating_the_human_is_capped():
    """Four actions against a human's forty-three is a hundredfold on the raw
    ratio and still only earns 115, which is why efficiency stops mattering."""
    assert level_score(4, 43) == EFFICIENCY_CAP
    assert level_score(1, 1000) == EFFICIENCY_CAP


def test_a_level_never_reached_earns_nothing():
    assert level_score(0, 50) == 0.0


def test_a_finished_game_caps_at_a_hundred():
    """ft09 under codex: every level at 115, ARC scored it 100.0 exactly. The
    cap is why a full clear cannot be improved on, however fast it was."""
    human = [43, 12, 23, 28, 65, 37]
    assert game_score([4, 7, 14, 22, 21, 21], human, cleared=6) == GAME_CAP


def test_an_unfinished_game_is_weighted_by_level_index():
    """ls20 under codex: five of seven levels, ARC scored it 32.388933682554814.

    The weighting is what makes a late level worth so much more than an early
    one — the two levels it never reached carry 13 of the 28 total weight.
    """
    human = [22, 123, 73, 84, 96, 192, 186]
    got = game_score([20, 186, 84, 73, 508, 1629, 0], human, cleared=5)
    assert round(got, 12) == 32.388933682555


def test_a_second_unfinished_game_agrees():
    """wa30 under codex: four of nine, ARC scored it 17.704608444343137."""
    human = [71, 119, 183, 98, 368, 68, 79, 442, 415]
    got = game_score([67, 119, 80, 166, 2068], human, cleared=4)
    assert round(got, 12) == 17.704608444343


def test_failing_a_level_costs_far_more_than_crawling_through_it():
    """The property the prompt was written around. On the same level, taking
    three times the human's actions costs a little; not finishing it costs the
    level and every level after it."""
    human = [100] * 6
    par = game_score([100] * 6, human, cleared=6)
    slow_on_third = game_score([100, 100, 300, 100, 100, 100], human, cleared=6)
    failed_third = game_score([100, 100, 300], human, cleared=2)
    assert par == 100.0
    assert round(par - slow_on_third, 1) == 12.7, "being slow is a scratch"
    assert round(par - failed_third, 1) == 85.7, "stopping is most of the score"
    assert failed_third < slow_on_third


def test_a_late_level_is_worth_more_than_an_early_one():
    """Weight is the level index, so the sixth level carries six times the
    first. Losing the same level late costs more than losing it early."""
    human = [100] * 6
    lost_early = game_score([100], human, cleared=1)
    lost_late = game_score([100] * 5, human, cleared=5)
    assert lost_late > lost_early
    assert round(lost_early, 2) == round(100 * 1 / 21, 2)
    assert round(lost_late, 2) == round(100 * 15 / 21, 2)


def test_weights_and_caps_are_the_documented_ones():
    assert (EFFICIENCY_CAP, GAME_CAP) == (115.0, 100.0)
