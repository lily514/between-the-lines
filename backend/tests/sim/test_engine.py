import time
from collections.abc import Iterable
from functools import cache
from itertools import pairwise

import numpy as np
import pytest

import btl.sim
from btl.league.league import League, generate_league
from btl.plant.planter import simulate_with_moments
from btl.plant.spec import parse_plant
from btl.schema.frames import to_left_to_right, to_spadl_frame
from btl.schema.match import Match
from btl.schema.possession import split_possessions
from btl.schema.snapshot import PlayerPosition
from btl.schema.vocab import ActionType, BodyPart, ConceptId, Phase, Result
from btl.sim.chain import CENTRE_SPOT, SIX_YARD_DEPTH, Side, Start, Step
from btl.sim.engine import simulate_match
from btl.sim.params import DEFAULT_PARAMS
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH, Point
from btl.sim.script import Script
from btl.sim.shape import FOUR_THREE_THREE
from tests.fixtures.imports import imports_by_module

SEEDS = range(5)
# These seeds' matches also hold planted line-breaking passes and counter-presses, so the
# invariants are checked with planting too.
PLANTED_SEEDS = (100, 101)


@cache
def league() -> League:
    return generate_league(np.random.default_rng(0))


@cache
def match(seed: int) -> Match:
    home, away = league().clubs[:2]
    if seed in PLANTED_SEEDS:
        request = parse_plant(["line_breaking_pass:1,2,3", "counter_press:1,2,3"])
        return simulate_with_moments(home, away, seed, request, away_formation=FOUR_THREE_THREE)
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


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_time_runs_forwards_within_each_half(seed: int) -> None:
    events = match(seed).events

    assert [event.period_id for event in events] == sorted(event.period_id for event in events)
    assert {event.period_id for event in events} == {1, 2}
    for before, after in pairwise(events):
        if before.period_id == after.period_id:
            assert before.time_seconds < after.time_seconds
    assert all(0 <= event.time_seconds < DEFAULT_PARAMS.period_seconds for event in events)


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_each_half_starts_with_a_kickoff(seed: int) -> None:
    played = match(seed)
    firsts = [next(e for e in played.events if e.period_id == period) for period in (1, 2)]

    assert [event.team_id for event in firsts] == [played.home_team_id, played.away_team_id]
    for event in firsts:
        assert event.action_type is ActionType.PASS
        assert event.phase is Phase.SET_PIECE
        assert (event.start_x, event.start_y) == (CENTRE_SPOT.x, CENTRE_SPOT.y)


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_restarts_are_set_pieces_taken_from_the_right_place(seed: int) -> None:
    events = match(seed).events

    for kind in (ActionType.THROW_IN, ActionType.GOALKICK):
        assert any(event.action_type is kind for event in events)
    for event in events:
        at_a_flag = event.start_x in (0, PITCH_LENGTH) and event.start_y in (0, PITCH_WIDTH)
        if event.action_type is ActionType.THROW_IN:
            assert event.start_y in (0, PITCH_WIDTH)
            assert event.bodypart is BodyPart.OTHER
        elif event.action_type is ActionType.GOALKICK:
            assert event.start_x in (SIX_YARD_DEPTH, PITCH_LENGTH - SIX_YARD_DEPTH)
        elif event.action_type in (ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT):
            assert at_a_flag
        else:
            continue
        assert event.phase is Phase.SET_PIECE


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_everything_happens_on_the_pitch(seed: int) -> None:
    played = match(seed)
    assert played.positions is not None

    for event in played.events:
        assert 0 <= event.start_x <= PITCH_LENGTH and 0 <= event.end_x <= PITCH_LENGTH
        assert 0 <= event.start_y <= PITCH_WIDTH and 0 <= event.end_y <= PITCH_WIDTH
    xy = played.positions.xy
    assert ((xy[..., 0] >= 0) & (xy[..., 0] <= PITCH_LENGTH)).all()
    assert ((xy[..., 1] >= 0) & (xy[..., 1] <= PITCH_WIDTH)).all()


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_possession_changes_hands_every_time_it_changes(seed: int) -> None:
    # A foul is made by the team without the ball, inside the other team's possession.
    events = [e for e in match(seed).events if e.action_type is not ActionType.FOUL]

    by_possession: dict[int, set[int]] = {}
    for event in events:
        by_possession.setdefault(event.possession_id, set()).add(event.team_id)
    assert all(len(teams) == 1 for teams in by_possession.values())
    assert sorted(by_possession) == list(range(len(by_possession)))
    for before, after in pairwise(events):
        if before.possession_id != after.possession_id and before.period_id == after.period_id:
            assert before.team_id != after.team_id


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_derived_possessions_match_the_engines_own(seed: int) -> None:
    events = match(seed).events

    derived = [(p.first, p.last) for p in split_possessions(events)]

    engine: dict[int, list[int]] = {}
    for event in events:
        engine.setdefault(event.possession_id, []).append(event.action_id)
    assert derived == [(ids[0], ids[-1]) for ids in engine.values()]


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_the_events_are_valid_spadl(seed: int) -> None:
    frame = to_spadl_frame(match(seed))

    assert len(frame) == len(match(seed).events)


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_every_snapshot_has_two_full_teams_and_the_actor_on_the_ball(seed: int) -> None:
    played = match(seed)

    answers = [played.events[moment.answer_action_id] for moment in played.planted]
    for event in (*played.events[::50], *answers):
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


def test_the_simulator_never_imports_planting() -> None:
    # Planting drives the simulator through `btl.sim.script.Director`, never the other way.
    for module, imported in imports_by_module(btl.sim).items():
        assert not [name for name in imported if name.startswith("btl.plant")], module


class CutOffByTheWhistle:
    """Writes the first possession as passes so slow the period ends before the answer."""

    def script(
        self,
        planted: int,
        period_id: int,
        clock: float,
        attack: Side,
        defence: Side,
        start: Start,
        rng: np.random.Generator,
    ) -> Script | None:
        if planted:
            return None
        ball = Point(50, 34)
        slow_pass = Step(
            0,
            ActionType.PASS,
            Result.SUCCESS,
            BodyPart.FOOT,
            ball,
            ball,
            DEFAULT_PARAMS.period_seconds,
            Phase.OPEN_PLAY,
        )
        return Script(
            steps=(slow_pass,) * 3,
            then=Start(ball, 0, ActionType.INTERCEPTION),
            shapes={},
            concept=ConceptId.LINE_BREAKING_PASS,
            difficulty=1,
            pause=1,
            answer=2,
        )


def test_a_moment_cut_off_by_the_whistle_is_an_error() -> None:
    home, away = league().clubs[:2]

    with pytest.raises(RuntimeError, match="period 1 ended"):
        simulate_match(home, away, 0, with_snapshots=False, director=CutOffByTheWhistle())


@pytest.mark.parametrize("seed", SEEDS)
def test_a_foul_is_by_the_team_without_the_ball_and_on_the_ball(seed: int) -> None:
    played = match(seed)
    assert played.positions is not None
    fouls = [e for e in played.events if e.action_type is ActionType.FOUL]

    assert fouls
    for foul in fouls:
        before, after = played.events[foul.action_id - 1], played.events[foul.action_id + 1]
        # Inside the fouled team's possession, which carries on with its free kick or play,
        # unless the half ends first.
        assert foul.possession_id == before.possession_id
        assert foul.team_id != before.team_id
        if after.period_id == foul.period_id:
            assert after.possession_id == foul.possession_id and after.team_id == before.team_id
        snapshot = played.snapshot(foul.action_id)
        assert snapshot is not None
        (fouler,) = [p for p in snapshot.positions if p.is_actor]
        assert (fouler.team_id, fouler.x, fouler.y) == (foul.team_id, foul.start_x, foul.start_y)


def in_offside_position(
    player: PlayerPosition, opponents: list[PlayerPosition], ball_x: float
) -> bool:
    # The Laws' test, written here independently of the simulator and the detectors.
    second_last = sorted((p.x for p in opponents), reverse=True)[1]
    return player.x > PITCH_LENGTH / 2 and player.x > ball_x and player.x > second_last


def check_pictures_agree_with_the_flag(matches: Iterable[Match]) -> None:
    flagged = 0
    for each in matches:
        played = to_left_to_right(each)
        for event, after in pairwise(played.events):
            if event.action_type is not ActionType.PASS or event.phase is Phase.SET_PIECE:
                continue
            snapshot = played.snapshot(event.action_id)
            assert snapshot is not None
            ours = [p for p in snapshot.positions if p.team_id == event.team_id]
            theirs = [p for p in snapshot.positions if p.team_id != event.team_id]
            if event.result is Result.OFFSIDE:
                flagged += 1
                mates = [p for p in ours if not p.is_actor and not p.is_goalkeeper]
                assert any(in_offside_position(p, theirs, event.start_x) for p in mates)
            elif event.result is Result.SUCCESS and after.team_id == event.team_id:
                receiver = next(p for p in ours if p.player_id == after.player_id)
                assert not in_offside_position(receiver, theirs, event.start_x)
    assert flagged > 0


def test_the_picture_at_a_pass_agrees_with_the_offside_flag() -> None:
    home, away = league().clubs[:2]
    many = (simulate_match(home, away, seed) for seed in range(10, 30))

    check_pictures_agree_with_the_flag([*(match(seed) for seed in PLANTED_SEEDS), *many])


@pytest.mark.slow
def test_the_picture_agrees_with_the_offside_flag_over_many_matches() -> None:
    home, away = league().clubs[:2]

    check_pictures_agree_with_the_flag(simulate_match(home, away, seed) for seed in range(200))


@pytest.mark.parametrize("seed", [*SEEDS, *PLANTED_SEEDS])
def test_at_every_kick_off_both_teams_are_in_their_own_halves(seed: int) -> None:
    played = match(seed)
    kickoffs = [
        event
        for event in played.events
        if event.action_type is ActionType.PASS
        and event.phase is Phase.SET_PIECE
        and (event.start_x, event.start_y) == (CENTRE_SPOT.x, CENTRE_SPOT.y)
    ]

    assert len(kickoffs) >= 2
    for event in kickoffs:
        snapshot = played.snapshot(event.action_id)
        assert snapshot is not None
        for player in snapshot.positions:
            if player.is_actor:
                continue
            # Stored: home attacks towards x = 105 in both halves.
            home = player.team_id == played.home_team_id
            assert player.x < PITCH_LENGTH / 2 if home else player.x > PITCH_LENGTH / 2
            if player.team_id != event.team_id:
                assert ((player.x - CENTRE_SPOT.x) ** 2 + (player.y - CENTRE_SPOT.y) ** 2) > 9.15**2
