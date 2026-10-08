from dataclasses import replace
from functools import cache
from itertools import pairwise

import numpy as np
import pytest

from btl.concepts.phase import (
    MIN_QUESTION_WINDOW,
    TRANSITION_SECONDS,
    PhaseOfPlay,
    PhaseTimeline,
    phase_timeline,
)
from btl.league.league import generate_league
from btl.plant.planter import simulate_with_moments
from btl.plant.spec import parse_plant
from btl.schema.event import Event
from btl.schema.match import Match
from btl.schema.possession import changes_hands_in_open_play, split_possessions
from btl.schema.vocab import ActionType, Phase, Result
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    GAME,
    HOME,
    HOME_MIDFIELDER,
    make_event,
)

SETTLED, TRANSITION = PhaseOfPlay.SETTLED, PhaseOfPlay.TRANSITION
DEAD = PhaseOfPlay.DEAD_BALL
EVERY_MOMENT = parse_plant(["line_breaking_pass:1,2,3", "counter_press:1,2,3"])


def match_of(
    *steps: tuple[str, ActionType, Result, float] | tuple[str, ActionType, Result, float, int],
) -> Match:
    """Events from (team, action, result, time[, period]) steps; positions don't matter here."""
    events: list[Event] = []
    for index, step in enumerate(steps):
        team, action, result, time = step[:4]
        period = step[4] if len(step) == 5 else 1
        player = HOME_MIDFIELDER if team == "home" else AWAY_MIDFIELDER
        event = make_event(
            index,
            HOME if team == "home" else AWAY,
            player,
            (50, 34),
            (55, 34),
            action,
            result,
            period_id=period,
        )
        events.append(replace(event, time_seconds=time))
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=tuple(events))


PASS, OK, FAIL = ActionType.PASS, Result.SUCCESS, Result.FAIL


def phases(match: Match) -> list[PhaseOfPlay]:
    return list(phase_timeline(match).action_phases)


def test_play_after_a_turnover_is_a_transition_until_four_passes() -> None:
    match = match_of(
        ("home", PASS, OK, 0),
        ("home", PASS, FAIL, 1),
        ("away", ActionType.INTERCEPTION, OK, 2),
        *(("away", PASS, OK, 3 + i) for i in range(5)),
    )

    # The interception and the four passes that follow are the transition; the fifth is settled.
    assert phases(match) == [SETTLED, SETTLED, *[TRANSITION] * 5, SETTLED]


def test_a_transition_ends_after_twelve_seconds_even_without_four_passes() -> None:
    match = match_of(
        ("home", PASS, FAIL, 0),
        ("away", ActionType.INTERCEPTION, OK, 1),
        ("away", ActionType.DRIBBLE, OK, 6),
        ("away", ActionType.DRIBBLE, OK, 1 + TRANSITION_SECONDS - 0.1),
        ("away", ActionType.DRIBBLE, OK, 1 + TRANSITION_SECONDS),
    )

    assert phases(match) == [SETTLED, TRANSITION, TRANSITION, TRANSITION, SETTLED]


def test_a_possession_that_starts_with_a_restart_is_settled() -> None:
    match = match_of(
        ("home", PASS, FAIL, 0),
        ("away", ActionType.THROW_IN, OK, 14),
        ("away", PASS, OK, 16),
    )

    assert phases(match) == [SETTLED, SETTLED, SETTLED]


def test_a_ball_out_of_play_is_dead_until_the_restart() -> None:
    match = match_of(
        ("home", PASS, OK, 0),
        ("home", PASS, FAIL, 3),
        ("away", ActionType.GOALKICK, OK, 24),
        ("away", PASS, OK, 27),
    )

    timeline = phase_timeline(match)
    dead = [segment for segment in timeline.segments if segment.phase is DEAD]

    assert [(s.start, s.end, s.first, s.last) for s in dead] == [(3, 24, 1, 2)]
    assert dead[0].long_enough_to_ask


def test_a_short_stoppage_is_too_short_to_ask_in() -> None:
    match = match_of(
        ("home", PASS, FAIL, 0),
        ("away", ActionType.THROW_IN, OK, MIN_QUESTION_WINDOW - 1),
    )

    (dead,) = [s for s in phase_timeline(match).segments if s.phase is DEAD]

    assert not dead.long_enough_to_ask


def test_a_goal_stops_play_until_the_kickoff_which_is_settled() -> None:
    match = match_of(
        ("home", ActionType.SHOT, OK, 0),
        ("away", PASS, OK, 45),
        ("away", PASS, OK, 47),
    )

    timeline = phase_timeline(match)

    assert [s.phase for s in timeline.segments] == [SETTLED, DEAD, SETTLED, PhaseOfPlay.FULL_TIME]
    assert phases(match) == [SETTLED, SETTLED, SETTLED]


def test_each_period_ends_with_its_break() -> None:
    match = match_of(
        ("home", PASS, OK, 0),
        ("home", PASS, OK, 2700, 1),
        ("away", PASS, OK, 0, 2),
        ("away", PASS, OK, 2700, 2),
    )

    breaks = [s for s in phase_timeline(match).segments if not s.phase.in_play]

    assert [(b.phase, b.period_id, b.start, b.seconds) for b in breaks] == [
        (PhaseOfPlay.HALF_TIME, 1, 2700, 0),
        (PhaseOfPlay.FULL_TIME, 2, 2700, 0),
    ]
    assert all(b.long_enough_to_ask for b in breaks)


@cache
def simulated(seed: int) -> tuple[Match, PhaseTimeline]:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    match = simulate_with_moments(home, away, seed, EVERY_MOMENT, with_snapshots=False)
    return match, phase_timeline(match)


@pytest.mark.parametrize("seed", range(10))
def test_segments_cover_each_period_without_gaps_or_overlaps(seed: int) -> None:
    match, timeline = simulated(seed)

    for period in (1, 2):
        events = [e for e in match.events if e.period_id == period]
        in_period = [s for s in timeline.segments if s.period_id == period]
        stretches = [s for s in in_period if s.phase in (SETTLED, TRANSITION, DEAD)]
        assert stretches[0].start == events[0].time_seconds
        assert stretches[-1].end == events[-1].time_seconds
        assert all(a.end == b.start for a, b in pairwise(stretches))
        assert in_period[-1].phase in (PhaseOfPlay.HALF_TIME, PhaseOfPlay.FULL_TIME)


@pytest.mark.parametrize("seed", range(10))
def test_every_turnover_in_open_play_starts_a_transition(seed: int) -> None:
    match, timeline = simulated(seed)
    possessions = split_possessions(match.events)

    for before, after in pairwise(possessions):
        if before.period_id == after.period_id and changes_hands_in_open_play(
            match.events[before.last], match.events[after.first]
        ):
            assert timeline.phase_of(after.first) is TRANSITION


@pytest.mark.parametrize("seed", range(10))
def test_planted_moments_all_happen_in_transitions(seed: int) -> None:
    match, timeline = simulated(seed)

    assert len(match.planted) == 6
    assert all(timeline.phase_of(m.answer_action_id) is TRANSITION for m in match.planted)


def test_dead_balls_long_enough_for_a_question_are_common() -> None:
    windows = [
        sum(s.phase is DEAD and s.long_enough_to_ask for s in simulated(seed)[1].segments)
        for seed in range(40)
    ]

    # Measured 25-48 a match (median 35): goal kicks, corners and goals; most throw-ins are
    # under 15 s.
    assert min(windows) >= 15
    assert 25 <= float(np.median(windows)) <= 50


def test_every_action_the_simulator_calls_a_transition_is_one_here() -> None:
    # The simulator's rule is narrower (8 s after winning the ball in open play), so its
    # transitions should all fall inside ours; the reverse needn't hold.
    for seed in range(40):
        match, timeline = simulated(seed)
        theirs = [e.action_id for e in match.events if e.phase is Phase.TRANSITION]
        assert theirs
        assert all(timeline.phase_of(action) is TRANSITION for action in theirs)
