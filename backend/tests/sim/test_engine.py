import time
from functools import cache
from itertools import pairwise

import numpy as np
import pytest

from btl.league.league import League, generate_league
from btl.schema.frames import to_spadl_frame
from btl.schema.match import Match
from btl.schema.possession import split_possessions
from btl.schema.vocab import ActionType, Phase
from btl.sim.chain import CENTRE_SPOT
from btl.sim.engine import simulate_match
from btl.sim.params import DEFAULT_PARAMS
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH
from btl.sim.shape import FOUR_THREE_THREE

SEEDS = range(5)


@cache
def league() -> League:
    return generate_league(np.random.default_rng(0))


@cache
def match(seed: int) -> Match:
    home, away = league().clubs[:2]
    return simulate_match(home, away, seed, away_formation=FOUR_THREE_THREE)


def test_same_seed_gives_the_same_match() -> None:
    home, away = league().clubs[:2]

    again = simulate_match(home, away, 3, away_formation=FOUR_THREE_THREE)

    assert again == match(3)


def test_different_seeds_give_different_matches() -> None:
    assert match(0).events != match(1).events


def test_turning_off_snapshots_keeps_the_same_events() -> None:
    home, away = league().clubs[:2]

    without = simulate_match(home, away, 2, away_formation=FOUR_THREE_THREE, with_snapshots=False)

    assert without.positions is None
    assert without.events == match(2).events


def test_a_club_cannot_play_itself() -> None:
    club = league().clubs[0]

    with pytest.raises(ValueError, match="can't play itself"):
        simulate_match(club, club, 0)


@pytest.mark.parametrize("seed", SEEDS)
def test_time_runs_forwards_within_each_half(seed: int) -> None:
    events = match(seed).events

    assert [event.period_id for event in events] == sorted(event.period_id for event in events)
    assert {event.period_id for event in events} == {1, 2}
    for before, after in pairwise(events):
        if before.period_id == after.period_id:
            assert before.time_seconds < after.time_seconds
    assert all(0 <= event.time_seconds < DEFAULT_PARAMS.period_seconds for event in events)


@pytest.mark.parametrize("seed", SEEDS)
def test_each_half_starts_with_a_kickoff(seed: int) -> None:
    played = match(seed)
    firsts = [next(e for e in played.events if e.period_id == period) for period in (1, 2)]

    assert [event.team_id for event in firsts] == [played.home_team_id, played.away_team_id]
    for event in firsts:
        assert event.action_type is ActionType.PASS
        assert event.phase is Phase.SET_PIECE
        assert (event.start_x, event.start_y) == (CENTRE_SPOT.x, CENTRE_SPOT.y)


@pytest.mark.parametrize("seed", SEEDS)
def test_everything_happens_on_the_pitch(seed: int) -> None:
    played = match(seed)
    assert played.positions is not None

    for event in played.events:
        assert 0 <= event.start_x <= PITCH_LENGTH and 0 <= event.end_x <= PITCH_LENGTH
        assert 0 <= event.start_y <= PITCH_WIDTH and 0 <= event.end_y <= PITCH_WIDTH
    xy = played.positions.xy
    assert ((xy[..., 0] >= 0) & (xy[..., 0] <= PITCH_LENGTH)).all()
    assert ((xy[..., 1] >= 0) & (xy[..., 1] <= PITCH_WIDTH)).all()


@pytest.mark.parametrize("seed", SEEDS)
def test_possession_changes_hands_every_time_it_changes(seed: int) -> None:
    events = match(seed).events

    by_possession: dict[int, set[int]] = {}
    for event in events:
        by_possession.setdefault(event.possession_id, set()).add(event.team_id)
    assert all(len(teams) == 1 for teams in by_possession.values())
    assert sorted(by_possession) == list(range(len(by_possession)))
    for before, after in pairwise(events):
        if before.possession_id != after.possession_id and before.period_id == after.period_id:
            assert before.team_id != after.team_id


@pytest.mark.parametrize("seed", SEEDS)
def test_derived_possessions_match_the_engines_own(seed: int) -> None:
    events = match(seed).events

    derived = [(p.first, p.last) for p in split_possessions(events)]

    engine: dict[int, list[int]] = {}
    for event in events:
        engine.setdefault(event.possession_id, []).append(event.action_id)
    assert derived == [(ids[0], ids[-1]) for ids in engine.values()]


@pytest.mark.parametrize("seed", SEEDS)
def test_the_events_are_valid_spadl(seed: int) -> None:
    frame = to_spadl_frame(match(seed))

    assert len(frame) == len(match(seed).events)


@pytest.mark.parametrize("seed", SEEDS)
def test_every_snapshot_has_two_full_teams_and_the_actor_on_the_ball(seed: int) -> None:
    played = match(seed)

    for event in played.events[::50]:
        snapshot = played.snapshot(event.action_id)
        assert snapshot is not None
        for team_id in (played.home_team_id, played.away_team_id):
            team = [p for p in snapshot.positions if p.team_id == team_id]
            assert len(team) == 11
            assert sum(p.is_goalkeeper for p in team) == 1
        (actor,) = [p for p in snapshot.positions if p.is_actor]
        assert (actor.x, actor.y) == (event.start_x, event.start_y)


def test_a_match_takes_well_under_a_second() -> None:
    home, away = league().clubs[:2]

    started = time.perf_counter()
    simulate_match(home, away, 0)

    assert time.perf_counter() - started < 1.0
