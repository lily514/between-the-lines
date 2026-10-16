from functools import cache

import numpy as np
import pytest

from btl.concepts.base import ConceptTag, match_context
from btl.concepts.restart import OUT_OF_PLAY, BallOutOfPlay
from btl.league.league import generate_league
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import out_and_restart
from tests.fixtures.matches import AWAY, HOME

PASS_OUT = (HOME, ActionType.PASS, Result.FAIL)


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, with_snapshots=False)


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return BallOutOfPlay().detect(match_context(match))


def test_a_pass_out_over_the_touchline_is_the_other_teams_throw_in() -> None:
    (tag,) = detect(out_and_restart(PASS_OUT, (AWAY, ActionType.THROW_IN, (60, 0))))

    assert tag.concept is ConceptId.RESTART
    assert tag.action_id == 0
    assert tag.span == (0, 1)
    assert tag.difficulty == 0.1
    # Away attacks the other way, so the throw is 45 m from its own goal line.
    assert tag.evidence == {
        "off an opponent": 0.0,
        "over a goal line": 0.0,
        "metres from a corner flag": 45.0,
    }


def test_a_throw_in_to_the_team_that_made_the_last_action_came_off_an_opponent() -> None:
    (tag,) = detect(out_and_restart(PASS_OUT, (HOME, ActionType.THROW_IN, (60, 68))))

    assert tag.evidence["off an opponent"] == 1.0
    assert tag.difficulty == 0.5


def test_a_shot_wide_is_a_goal_kick_and_a_corner_off_a_defender_is_harder() -> None:
    shot_wide = (HOME, ActionType.SHOT, Result.FAIL)
    cross = (HOME, ActionType.CROSS, Result.FAIL)

    (goal_kick,) = detect(out_and_restart(shot_wide, (AWAY, ActionType.GOALKICK, (99.5, 34))))
    (corner,) = detect(out_and_restart(cross, (HOME, ActionType.CORNER_CROSSED, (105, 0))))

    assert goal_kick.difficulty == 0.3
    assert goal_kick.evidence == {"off an opponent": 0.0, "over a goal line": 1.0}
    assert corner.difficulty == 0.75
    assert corner.evidence == {"off an opponent": 1.0, "over a goal line": 1.0}


def test_a_defenders_clearance_behind_is_a_plain_corner() -> None:
    clearance = (AWAY, ActionType.CLEARANCE, Result.SUCCESS)

    (tag,) = detect(out_and_restart(clearance, (HOME, ActionType.CORNER_SHORT, (105, 68))))

    assert tag.difficulty == 0.4
    assert tag.evidence["off an opponent"] == 0.0


@pytest.mark.parametrize(("x", "difficulty"), [(3.0, 0.25), (102.0, 0.25), (10.0, 0.1)])
def test_a_throw_in_near_a_corner_flag_is_harder(x: float, difficulty: float) -> None:
    (tag,) = detect(out_and_restart(PASS_OUT, (AWAY, ActionType.THROW_IN, (x, 0))))

    assert tag.difficulty == pytest.approx(difficulty)


@pytest.mark.parametrize(
    "kind", [ActionType.FREEKICK_SHORT, ActionType.SHOT_PENALTY, ActionType.PASS]
)
def test_restarts_after_a_foul_or_a_goal_are_not_tagged(kind: ActionType) -> None:
    assert detect(out_and_restart(PASS_OUT, (AWAY, kind, (60, 34)))) == ()


def test_a_restart_that_opens_a_period_is_not_tagged() -> None:
    match = out_and_restart(PASS_OUT, (AWAY, ActionType.THROW_IN, (60, 0)), period=2)

    assert detect(match) == ()


@pytest.mark.parametrize("seed", range(3))
def test_every_throw_in_corner_and_goal_kick_in_a_match_is_tagged_once(seed: int) -> None:
    match = simulated(seed)
    restarts = [
        e.action_id
        for before, e in zip(match.events, match.events[1:], strict=False)
        if e.action_type in OUT_OF_PLAY and before.period_id == e.period_id
    ]

    tags = detect(match)

    assert [tag.span[1] for tag in tags] == restarts
    assert all(tag.difficulty is not None and 0 <= tag.difficulty <= 1 for tag in tags)
    assert any(tag.evidence["off an opponent"] for tag in tags)
