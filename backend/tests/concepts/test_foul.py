import numpy as np
import pytest

from btl.concepts.base import ConceptTag, match_context
from btl.concepts.foul import (
    ADVANTAGE,
    EXPLAINED_BOOKING,
    NEAR_THE_BOX,
    ON_THE_BOX_LINE,
    PLAIN,
    FoulCommitted,
    metres_from_box,
)
from btl.league.league import generate_league
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import fouled

MIDFIELD = (60.0, 34.0)


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return FoulCommitted().detect(match_context(match))


def test_a_foul_in_midfield_gives_the_fouled_team_a_free_kick() -> None:
    (tag,) = detect(fouled(MIDFIELD))

    assert tag.concept is ConceptId.FOUL
    assert tag.action_id == 3
    assert tag.span == (3, 4)
    assert tag.difficulty == PLAIN
    assert tag.evidence["penalty"] == 0.0
    assert tag.evidence["advantage"] == 0.0
    assert tag.evidence["metres from the box"] == 28.5


def test_a_foul_inside_the_box_is_a_penalty() -> None:
    (tag,) = detect(fouled((95, 30), then=ActionType.SHOT_PENALTY))

    assert tag.evidence["penalty"] == 1.0
    assert tag.evidence["metres from the box"] < 0


@pytest.mark.parametrize(
    ("x", "difficulty"), [(88.5, ON_THE_BOX_LINE), (87.0, NEAR_THE_BOX), (80.0, PLAIN)]
)
def test_a_foul_near_the_box_line_is_a_hard_call(x: float, difficulty: float) -> None:
    (tag,) = detect(fouled((x, 34)))

    assert tag.difficulty == difficulty


def test_the_box_line_counts_as_inside() -> None:
    assert metres_from_box(16.5, 34) == 0.0
    assert metres_from_box(10, 34) == -6.5
    assert metres_from_box(20.5, 34) == 4.0
    assert metres_from_box(16.5 + 3, 34 + 20.16 + 4) == pytest.approx(5.0)


def test_a_booking_for_stopping_a_promising_attack_is_explained() -> None:
    (tag,) = detect(fouled(MIDFIELD, result=Result.YELLOW_CARD))

    assert tag.evidence["booked"] == 1.0
    assert tag.evidence["promising attack"] == 1.0
    assert tag.difficulty == EXPLAINED_BOOKING


def test_a_booking_in_settled_play_or_deep_in_their_own_half_is_not_explained() -> None:
    (settled,) = detect(fouled(MIDFIELD, passes_first=5, result=Result.YELLOW_CARD))
    (deep,) = detect(fouled((20, 34), result=Result.YELLOW_CARD))

    assert settled.evidence["promising attack"] == 0.0
    assert deep.evidence["promising attack"] == 0.0
    assert settled.difficulty == deep.difficulty == PLAIN


def test_play_going_on_after_a_foul_is_advantage() -> None:
    (tag,) = detect(fouled(MIDFIELD, then=ActionType.PASS))

    assert tag.evidence["advantage"] == 1.0
    assert tag.difficulty == ADVANTAGE


@pytest.mark.parametrize("seed", range(5))
def test_in_simulated_matches_the_box_decides_free_kick_or_penalty(seed: int) -> None:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    match = simulate_match(home, away, seed, with_snapshots=False)

    tags = detect(match)

    assert len(tags) == sum(e.action_type is ActionType.FOUL for e in match.events[:-1])
    for tag in tags:
        if not tag.evidence["advantage"]:
            inside = tag.evidence["metres from the box"] <= 0
            assert tag.evidence["penalty"] == float(inside)


def test_most_simulated_bookings_are_explained() -> None:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    booked = [
        tag
        for seed in range(40)
        for tag in detect(simulate_match(home, away, seed, with_snapshots=False))
        if tag.evidence["booked"]
    ]

    explained = sum(tag.evidence["promising attack"] == 1.0 for tag in booked)
    assert explained >= 0.75 * len(booked)
