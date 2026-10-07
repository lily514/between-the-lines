# pyright: basic
# pandas is only partially typed; see CLAUDE.md on edge modules.
from dataclasses import replace

import numpy as np
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st
from pandera.typing import DataFrame
from socceraction.spadl import SPADLSchema, play_left_to_right

from btl.schema.event import Event
from btl.schema.frames import (
    SPADL_COLUMNS,
    events_from_frames,
    positions_from_snapshot_frame,
    to_extension_frame,
    to_left_to_right,
    to_snapshot_frame,
    to_spadl_frame,
)
from btl.schema.ids import ActionId, PlayerId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, BodyPart, Phase, Result
from tests.fixtures.matches import AWAY, GAME, HOME, six_event_match


def test_spadl_frame_has_exactly_the_spadl_columns_and_validates() -> None:
    frame = to_spadl_frame(six_event_match())

    assert tuple(frame.columns) == SPADL_COLUMNS
    assert list(frame.original_event_id) == [f"g1-e000{i}" for i in range(6)]
    SPADLSchema.validate(frame)


def test_spadl_and_extension_frames_round_trip_to_the_same_events() -> None:
    match = replace(
        six_event_match(),
        events=tuple(
            replace(event, planted_moment_id=7 if event.action_id == 2 else None)
            for event in six_event_match().events
        ),
    )

    rebuilt = events_from_frames(to_spadl_frame(match), to_extension_frame(match))

    assert rebuilt == match.events


def test_snapshot_frame_round_trips_to_the_same_positions() -> None:
    match = six_event_match()
    assert match.positions is not None

    rebuilt = positions_from_snapshot_frame(to_snapshot_frame(match), len(match.events))

    assert rebuilt == match.positions


def test_snapshot_frame_leaves_out_unknown_positions() -> None:
    frame = to_snapshot_frame(six_event_match())

    assert 4 not in set(frame.action_id)
    assert len(frame) == 5 * 4


def test_snapshot_frame_is_empty_without_positions() -> None:
    frame = to_snapshot_frame(replace(six_event_match(), positions=None))

    assert frame.empty


def test_left_to_right_flips_away_events_and_their_snapshots_together() -> None:
    match = six_event_match()

    events = to_spadl_frame(match, left_to_right=True).set_index("action_id")
    snapshots = to_snapshot_frame(match, left_to_right=True)

    # Action 3: away's interception at (85, 40) is seen from away's side: (105-85, 68-40).
    assert (events.loc[3, "start_x"], events.loc[3, "start_y"]) == (20, 28)
    interceptor = snapshots[(snapshots.action_id == 3) & snapshots.is_actor].iloc[0]
    assert (interceptor.x, interceptor.y) == (20, 28)
    away_keeper = snapshots[(snapshots.action_id == 3) & (snapshots.player_id == 20)].iloc[0]
    assert (away_keeper.x, away_keeper.y) == (105 - 98, 68 - 36)


def test_left_to_right_leaves_home_events_and_their_snapshots_untouched() -> None:
    match = six_event_match()
    home_actions = [event.action_id for event in match.events if event.team_id == HOME]

    flipped_events = to_spadl_frame(match, left_to_right=True)
    flipped_snapshots = to_snapshot_frame(match, left_to_right=True)

    stored_events = to_spadl_frame(match)
    stored_snapshots = to_snapshot_frame(match)
    assert flipped_events[flipped_events.action_id.isin(home_actions)].equals(
        stored_events[stored_events.action_id.isin(home_actions)]
    )
    assert flipped_snapshots[flipped_snapshots.action_id.isin(home_actions)].equals(
        stored_snapshots[stored_snapshots.action_id.isin(home_actions)]
    )


@st.composite
def matches(draw: st.DrawFn) -> Match:
    """Random matches whose events are valid but otherwise arbitrary."""
    n_events = draw(st.integers(min_value=0, max_value=30))
    xs = st.floats(min_value=0, max_value=105)
    ys = st.floats(min_value=0, max_value=68)
    events = tuple(
        Event(
            game_id=GAME,
            action_id=ActionId(action_id),
            period_id=draw(st.sampled_from([1, 2])),
            time_seconds=draw(st.floats(min_value=0, max_value=3000)),
            team_id=draw(st.sampled_from([HOME, AWAY])),
            player_id=PlayerId(draw(st.integers(min_value=1, max_value=99))),
            start_x=draw(xs),
            start_y=draw(ys),
            end_x=draw(xs),
            end_y=draw(ys),
            action_type=draw(st.sampled_from(ActionType)),
            result=draw(st.sampled_from(Result)),
            bodypart=draw(st.sampled_from(BodyPart)),
            possession_id=draw(st.integers(min_value=0, max_value=500)),
            phase=draw(st.sampled_from(Phase)),
            planted_moment_id=draw(st.none() | st.integers(min_value=0, max_value=10)),
        )
        for action_id in range(n_events)
    )
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events)


@settings(max_examples=50, deadline=None)
@given(matches())
def test_any_valid_match_gives_valid_spadl_in_both_directions(match: Match) -> None:
    SPADLSchema.validate(to_spadl_frame(match))
    SPADLSchema.validate(to_spadl_frame(match, left_to_right=True))


@settings(max_examples=50, deadline=None)
@given(matches())
def test_any_valid_match_round_trips_through_its_frames(match: Match) -> None:
    rebuilt = events_from_frames(to_spadl_frame(match), to_extension_frame(match))

    assert rebuilt == match.events


def test_flipping_twice_gives_back_the_stored_coordinates() -> None:
    match = six_event_match()
    once = to_spadl_frame(match, left_to_right=True)
    away = once.team_id == AWAY

    np.testing.assert_allclose(
        105 - once.loc[away, "start_x"], to_spadl_frame(match).loc[away, "start_x"]
    )


def test_our_left_to_right_flip_agrees_with_socceractions() -> None:
    match = six_event_match()

    ours = to_spadl_frame(to_left_to_right(match))
    theirs = play_left_to_right(DataFrame[SPADLSchema](to_spadl_frame(match)), home_team_id=HOME)

    pd.testing.assert_frame_equal(ours, pd.DataFrame(theirs))


def test_the_left_to_right_view_flips_snapshots_with_their_actions() -> None:
    match = six_event_match()

    flipped = to_left_to_right(match)

    away_action = match.events[3]
    assert away_action.team_id == AWAY
    assert flipped.events[3].start_x == 105 - away_action.start_x
    before, after = match.snapshot(away_action.action_id), flipped.snapshot(away_action.action_id)
    assert before is not None and after is not None
    assert [(p.x, p.y) for p in after.positions] == [
        (105 - p.x, 68 - p.y) for p in before.positions
    ]
    assert flipped.events[0] == match.events[0]
    assert flipped.snapshot(match.events[0].action_id) == match.snapshot(match.events[0].action_id)
