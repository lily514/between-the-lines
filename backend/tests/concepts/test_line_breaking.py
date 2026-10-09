from functools import cache

import numpy as np
import pytest

from btl.concepts.base import ConceptTag, match_context
from btl.concepts.line_breaking import LineBreakingPass
from btl.league.league import generate_league
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from btl.sim.shape import FOUR_THREE_THREE
from tests.fixtures.concepts import (
    BACK_LINE,
    MIDFIELD_LINE,
    TWO_FORWARDS,
    Spot,
    mirrored,
    one_pass,
)
from tests.fixtures.matches import AWAY, HOME

# A line whose two middle players leave a gap of the given width around the pitch's centre.
NARROW_8 = ((50, 10), (50, 30), (50, 38), (50, 58))
WIDE_16 = ((50, 5), (50, 26), (50, 42), (50, 63))
WIDE_22 = ((50, 2), (50, 23), (50, 45), (50, 66))


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return LineBreakingPass().detect(match_context(match))


def only_tag(start: Spot, end: Spot, defenders: tuple[Spot, ...]) -> ConceptTag:
    (tag,) = detect(one_pass(start, end, defenders))
    return tag


def test_a_pass_through_the_midfield_line_breaks_one_line() -> None:
    tag = only_tag((40, 34), (60, 34), MIDFIELD_LINE + BACK_LINE)

    assert tag.concept is ConceptId.LINE_BREAKING_PASS
    assert tag.evidence == {"lines broken": 1, "gap (m)": 12.0}


def test_a_pass_through_both_banks_of_four_breaks_two_lines() -> None:
    tag = only_tag((40, 34), (85, 34), MIDFIELD_LINE + BACK_LINE)

    assert tag.evidence == {"lines broken": 2, "gap (m)": 12.0}
    one_line = only_tag((40, 34), (60, 34), MIDFIELD_LINE + BACK_LINE)
    assert tag.difficulty is not None and one_line.difficulty is not None
    assert tag.difficulty == pytest.approx(one_line.difficulty + 0.2)


def test_a_sideways_pass_breaks_nothing() -> None:
    assert detect(one_pass((40, 20), (45, 50), MIDFIELD_LINE + BACK_LINE)) == ()


def test_two_forwards_are_not_a_line() -> None:
    over_the_forwards = one_pass((40, 34), (65, 34), TWO_FORWARDS + BACK_LINE)
    on_through_the_back_line = one_pass((40, 34), (85, 34), TWO_FORWARDS + BACK_LINE)

    assert detect(over_the_forwards) == ()
    (tag,) = detect(on_through_the_back_line)
    assert tag.evidence["lines broken"] == 1


def test_a_pass_around_the_end_of_a_line_does_not_break_it() -> None:
    assert detect(one_pass((40, 5), (60, 5), MIDFIELD_LINE)) == ()


def test_a_failed_pass_breaks_nothing() -> None:
    assert detect(one_pass((40, 34), (60, 34), MIDFIELD_LINE, result=Result.FAIL)) == ()


def test_without_a_snapshot_nothing_is_found() -> None:
    assert detect(one_pass((40, 34), (60, 34), MIDFIELD_LINE, with_snapshot=False)) == ()


def test_the_away_team_breaks_lines_attacking_the_other_way() -> None:
    away_pass = one_pass((65, 34), (45, 34), mirrored(MIDFIELD_LINE + BACK_LINE), team=AWAY)

    (tag,) = detect(away_pass)

    assert tag.evidence == {"lines broken": 1, "gap (m)": 12.0}


def test_a_pass_that_was_not_played_is_measured_by_the_same_rule() -> None:
    # The pass in the match failed, so the detector finds nothing; the snapshot still holds the
    # lines, and passes that never happened can be measured against them.
    match = one_pass((40, 34), (60, 34), MIDFIELD_LINE + BACK_LINE, result=Result.FAIL)
    snapshot = match_context(match).snapshot(ActionId(0))
    assert snapshot is not None
    detector = LineBreakingPass()

    through_midfield = detector.lines_broken(snapshot, HOME, (40, 34), (60, 34))
    through_both = detector.lines_broken(snapshot, HOME, (40, 34), (85, 34))
    sideways = detector.lines_broken(snapshot, HOME, (40, 20), (45, 50))

    assert detect(match) == ()
    assert through_midfield == pytest.approx((12.0,))
    assert len(through_both) == 2
    assert through_both[0] == pytest.approx(12.0)
    assert sideways == ()


def test_a_narrower_gap_is_harder() -> None:
    wide = only_tag((40, 34), (60, 34), WIDE_16)
    narrow = only_tag((40, 34), (60, 34), NARROW_8)

    assert wide.difficulty is not None and narrow.difficulty is not None
    assert narrow.difficulty > wide.difficulty
    assert only_tag((40, 34), (60, 34), WIDE_22).difficulty == 0


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, away_formation=FOUR_THREE_THREE)


@pytest.mark.parametrize("seed", range(2))
def test_in_simulated_play_every_tag_is_a_completed_forward_pass(seed: int) -> None:
    played = simulated(seed)
    ctx = match_context(played)

    tags = detect(played)

    assert tags
    for tag in tags:
        event = ctx.events[tag.action_id]
        assert event.action_type is ActionType.PASS
        assert event.result is Result.SUCCESS
        assert event.end_x > event.start_x
        assert tag.difficulty is not None and 0 <= tag.difficulty <= 1
        assert tag.evidence["lines broken"] >= 1
