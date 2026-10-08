from dataclasses import replace

import numpy as np
import pytest

from btl.schema.ids import ActionId, TeamId
from btl.schema.moment import PlantedMoment
from btl.schema.snapshot import Positions
from btl.schema.vocab import ConceptId
from tests.fixtures.matches import (
    AWAY_KEEPER,
    AWAY_MIDFIELDER,
    HOME_KEEPER,
    HOME_MIDFIELDER,
    six_event_match,
)


def test_action_ids_must_run_in_order() -> None:
    match = six_event_match()
    swapped = (match.events[1], match.events[0], *match.events[2:])

    with pytest.raises(ValueError, match="action_id"):
        replace(match, events=swapped)


def test_events_must_be_by_one_of_the_two_teams() -> None:
    match = six_event_match()
    stranger = replace(match.events[0], team_id=TeamId(99))

    with pytest.raises(ValueError, match="team 99"):
        replace(match, events=(stranger, *match.events[1:]))


@pytest.mark.parametrize(("pause", "answer"), [(4, 6), (5, 4)])
def test_a_planted_moment_must_pause_before_its_answer_within_the_match(
    pause: int, answer: int
) -> None:
    moment = PlantedMoment(ConceptId.LINE_BREAKING_PASS, 1, ActionId(pause), ActionId(answer))

    with pytest.raises(ValueError, match="planted moment"):
        replace(six_event_match(), planted=(moment,))


def test_positions_must_cover_every_action() -> None:
    match = six_event_match()
    assert match.positions is not None
    short = Positions(match.positions.slots, match.positions.xy[:3])

    with pytest.raises(ValueError, match="positions cover 3 actions"):
        replace(match, positions=short)


def test_positions_reject_an_array_that_does_not_match_the_slots() -> None:
    with pytest.raises(ValueError, match="shape"):
        Positions(slots=(), xy=np.zeros((2, 1, 2)))


def test_snapshot_marks_the_actor_and_the_goalkeepers() -> None:
    snapshot = six_event_match().snapshot(ActionId(3))

    assert snapshot is not None
    by_player = {position.player_id: position for position in snapshot.positions}
    assert [p for p in by_player if by_player[p].is_actor] == [AWAY_MIDFIELDER]
    assert {p for p in by_player if by_player[p].is_goalkeeper} == {HOME_KEEPER, AWAY_KEEPER}
    assert (by_player[HOME_MIDFIELDER].x, by_player[HOME_MIDFIELDER].y) == (58, 33)


def test_snapshot_is_none_when_no_positions_are_known() -> None:
    match = six_event_match()

    assert match.snapshot(ActionId(4)) is None
    assert replace(match, positions=None).snapshot(ActionId(0)) is None


def test_matches_with_the_same_unknown_positions_are_equal() -> None:
    assert six_event_match() == six_event_match()
