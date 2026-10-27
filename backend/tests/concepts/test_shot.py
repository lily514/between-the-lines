from functools import cache

import numpy as np
import pytest

from btl.concepts.base import ConceptTag, match_context
from btl.concepts.shot import SHOTS, ChanceFrom, Shot, ShotOutcome, ShotZone, shot_zone
from btl.league.league import generate_league
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import chance_and_shot
from tests.fixtures.matches import AWAY, HOME

IN_THE_BOX = (95.0, 30.0)
SIX_YARDS = (101.0, 36.0)
OUTSIDE = (80.0, 34.0)
# Dead centre of the goal, 3.66 m from each post; just inside and just wide of a post.
CENTRE = (105.0, 34.0)
INSIDE_THE_POST = (105.0, 37.3)
JUST_WIDE = (105.0, 38.16)


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, with_snapshots=False)


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return Shot().detect(match_context(match))


def evidence(match: Match) -> tuple[ShotOutcome, ShotZone, ChanceFrom]:
    (tag,) = detect(match)
    return (
        ShotOutcome(int(tag.evidence["outcome"])),
        ShotZone(int(tag.evidence["zone"])),
        ChanceFrom(int(tag.evidence["chance from"])),
    )


def test_a_shot_from_the_box_after_a_pass_that_the_keeper_saves() -> None:
    (tag,) = detect(chance_and_shot(IN_THE_BOX, CENTRE, saved=True))

    assert tag.concept is ConceptId.SHOT
    assert (tag.action_id, tag.span) == (1, (0, 1))
    assert tag.evidence == {
        "outcome": float(ShotOutcome.SAVED),
        "zone": float(ShotZone.PENALTY_AREA),
        "chance from": float(ChanceFrom.PASS),
        "metres from goal": 10.8,
        "metres from a post": 3.7,
    }
    assert tag.difficulty == 0.0


def test_a_header_from_a_cross_in_the_six_yard_box_that_goes_in() -> None:
    match = chance_and_shot(
        SIX_YARDS, INSIDE_THE_POST, result=Result.SUCCESS, made_by=ActionType.CROSS
    )

    assert evidence(match) == (ShotOutcome.SCORED, ShotZone.SIX_YARD_BOX, ChanceFrom.CROSS)


def test_a_shot_from_outside_after_a_dribble_that_goes_just_wide_is_a_hard_call() -> None:
    match = chance_and_shot(OUTSIDE, JUST_WIDE, made_by=ActionType.DRIBBLE)

    (tag,) = detect(match)

    assert evidence(match) == (ShotOutcome.OFF_TARGET, ShotZone.OUTSIDE_THE_BOX, ChanceFrom.DRIBBLE)
    assert tag.evidence["metres from a post"] == 0.5
    assert tag.difficulty == pytest.approx(0.83)


def test_a_direct_free_kick_is_its_own_source_and_a_penalty_is_not_tagged() -> None:
    free_kick = chance_and_shot(OUTSIDE, CENTRE, kind=ActionType.SHOT_FREEKICK, saved=True)
    penalty = chance_and_shot((94.0, 34.0), CENTRE, kind=ActionType.SHOT_PENALTY, saved=True)

    assert evidence(free_kick)[2] is ChanceFrom.FREE_KICK
    assert detect(penalty) == ()


def test_a_shot_straight_after_winning_the_ball_comes_from_a_loose_ball() -> None:
    match = chance_and_shot(IN_THE_BOX, CENTRE, made_by=None, saved=True)

    (tag,) = detect(match)

    assert tag.span == (1, 1)
    assert evidence(match) == (ShotOutcome.SAVED, ShotZone.PENALTY_AREA, ChanceFrom.LOOSE_BALL)


def test_a_corner_or_a_free_kick_cross_counts_as_a_cross() -> None:
    corner = chance_and_shot(SIX_YARDS, CENTRE, made_by=ActionType.CORNER_CROSSED, saved=True)
    crossed = chance_and_shot(SIX_YARDS, CENTRE, made_by=ActionType.FREEKICK_CROSSED, saved=True)
    short = chance_and_shot(IN_THE_BOX, CENTRE, made_by=ActionType.FREEKICK_SHORT, saved=True)

    assert evidence(corner)[2] is evidence(crossed)[2] is ChanceFrom.CROSS
    assert evidence(short)[2] is ChanceFrom.PASS


def test_the_away_team_shoots_the_other_way() -> None:
    match = chance_and_shot(SIX_YARDS, INSIDE_THE_POST, result=Result.SUCCESS, team=AWAY)

    (tag,) = detect(match)

    assert evidence(match)[:2] == (ShotOutcome.SCORED, ShotZone.SIX_YARD_BOX)
    assert tag.evidence["metres from goal"] == pytest.approx(4.5, abs=0.05)


@pytest.mark.parametrize(
    ("spot", "zone"),
    [
        ((100.0, 34.0), ShotZone.SIX_YARD_BOX),
        ((99.5, 43.0), ShotZone.SIX_YARD_BOX),
        ((99.0, 44.0), ShotZone.PENALTY_AREA),
        ((90.0, 34.0), ShotZone.PENALTY_AREA),
        ((88.0, 34.0), ShotZone.OUTSIDE_THE_BOX),
        ((100.0, 10.0), ShotZone.OUTSIDE_THE_BOX),
    ],
)
def test_the_zone_follows_the_boxes(spot: tuple[float, float], zone: ShotZone) -> None:
    assert shot_zone(*spot) is zone


@pytest.mark.parametrize("seed", range(3))
def test_in_simulated_play_every_shot_is_tagged_once_with_a_true_outcome(seed: int) -> None:
    played = simulated(seed)
    shots = [e for e in played.events if e.action_type in SHOTS]

    tags = detect(played)

    assert [tag.action_id for tag in tags] == [e.action_id for e in shots]
    assert len(tags) > 10
    for tag in tags:
        shot = played.events[tag.action_id]
        outcome = ShotOutcome(int(tag.evidence["outcome"]))
        # A shot can be the last action of the match, with nothing after it.
        after = played.events[tag.action_id + 1 : tag.action_id + 2]
        saved = bool(after) and after[0].action_type is ActionType.KEEPER_SAVE
        assert (outcome is ShotOutcome.SCORED) == (shot.result is Result.SUCCESS)
        assert (outcome is ShotOutcome.SAVED) == (shot.result is not Result.SUCCESS and saved)
        assert tag.difficulty is not None and 0 <= tag.difficulty <= 1
        assert tag.span[0] <= tag.action_id
        assert played.events[tag.span[0]].team_id == shot.team_id
        attacks_towards_105 = shot.team_id == HOME
        x = shot.start_x if attacks_towards_105 else 105 - shot.start_x
        assert (ShotZone(int(tag.evidence["zone"])) is ShotZone.OUTSIDE_THE_BOX) == (
            x < 88.5 or abs(shot.start_y - 34) > 20.16
        )


def test_simulated_matches_hold_every_outcome_and_most_sources() -> None:
    tags = [tag for seed in range(3) for tag in detect(simulated(seed))]

    assert {ShotOutcome(int(t.evidence["outcome"])) for t in tags} == set(ShotOutcome)
    assert {ChanceFrom.CROSS, ChanceFrom.PASS, ChanceFrom.DRIBBLE, ChanceFrom.FREE_KICK} <= {
        ChanceFrom(int(t.evidence["chance from"])) for t in tags
    }
