from dataclasses import replace

import pytest

from btl.schema.vocab import ActionType, Result
from btl.sim.stats import match_stats
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    HOME,
    HOME_WINGER,
    make_event,
    six_event_match,
)


def test_match_stats_counts_passes_shots_and_restarts() -> None:
    fixture = six_event_match()
    extra = (
        make_event(6, AWAY, AWAY_MIDFIELDER, (50, 30), (50, 0), result=Result.FAIL),
        make_event(7, HOME, HOME_WINGER, (50, 68), (60, 60), ActionType.THROW_IN),
        make_event(8, HOME, HOME_WINGER, (95, 34), (105, 34), ActionType.SHOT),
        make_event(9, HOME, HOME_WINGER, (95, 34), (105, 40), ActionType.SHOT, Result.FAIL),
        make_event(10, HOME, HOME_WINGER, (105, 0), (95, 34), ActionType.CORNER_CROSSED),
    )
    played = replace(fixture, events=fixture.events + extra, positions=None)

    stats = match_stats(played)

    assert (stats.passes, stats.completed_passes) == (4, 2)
    assert stats.pass_completion == pytest.approx(0.5)
    assert (stats.shots, stats.goals) == (2, 1)
    assert (stats.throw_ins, stats.goal_kicks, stats.corners) == (1, 0, 1)
    assert stats.throw_in_lengths == (pytest.approx(12.8, abs=0.1),)
    assert (stats.actions, stats.on_touchline) == (11, 2)
