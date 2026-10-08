# pyright: basic
# pandas and socceraction are only partially typed; see CLAUDE.md on edge modules.
"""Conversions between a `Match` and pandas DataFrames.

Three frames describe a match:

- the SPADL frame: exactly socceraction's columns, validated with its strict ``SPADLSchema``;
- the extension frame: our fields SPADL has no columns for, keyed by ``(game_id, action_id)``;
- the snapshot frame: one row per known player position per action.

This is the only module that flips coordinates. `to_left_to_right` mirrors every away-team
action and its snapshot as if the acting team attacks towards x = 105; the frame functions'
``left_to_right=True`` option uses it. `seen_by` mirrors the whole match for one team.
"""

from dataclasses import replace

import numpy as np
import pandas as pd
from socceraction.spadl import SPADLSchema

from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId, PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot, Positions
from btl.schema.vocab import ActionType, BodyPart, Phase, Result

SPADL_COLUMNS = (
    "game_id",
    "original_event_id",
    "action_id",
    "period_id",
    "time_seconds",
    "team_id",
    "player_id",
    "start_x",
    "start_y",
    "end_x",
    "end_y",
    "type_id",
    "result_id",
    "bodypart_id",
)
EXTENSION_COLUMNS = ("game_id", "action_id", "possession_id", "phase", "planted_moment_id")
SNAPSHOT_COLUMNS = (
    "game_id",
    "action_id",
    "player_id",
    "team_id",
    "x",
    "y",
    "is_actor",
    "is_goalkeeper",
)


def to_left_to_right(match: Match) -> Match:
    """The match as if every action's team attacks towards x = 105.

    Away-team actions, and the snapshots taken at them, are mirrored: ``x → 105 - x`` and
    ``y → 68 - y``, as socceraction's ``play_left_to_right`` does. Home actions are unchanged.
    The result is a view for analysis; never save it as a match.
    """
    return _mirrored(match, [event.team_id != match.home_team_id for event in match.events])


def seen_by(match: Match, team_id: TeamId) -> Match:
    """The whole match as if ``team_id`` attacks towards x = 105, both teams mirrored together.

    Unlike `to_left_to_right`, the pitch doesn't turn round when the ball changes hands, so
    this suits watching play unfold. The result is a view; never save it as a match.
    """
    return _mirrored(match, [team_id != match.home_team_id] * len(match.events))


def _mirrored(match: Match, flip: list[bool]) -> Match:
    events = tuple(
        replace(
            event,
            start_x=PITCH_LENGTH - event.start_x,
            start_y=PITCH_WIDTH - event.start_y,
            end_x=PITCH_LENGTH - event.end_x,
            end_y=PITCH_WIDTH - event.end_y,
        )
        if flipped
        else event
        for event, flipped in zip(match.events, flip, strict=True)
    )
    positions = match.positions
    if positions is not None and any(flip):
        xy = positions.xy.copy()
        rows = np.array(flip)
        xy[rows, :, 0] = PITCH_LENGTH - xy[rows, :, 0]
        xy[rows, :, 1] = PITCH_WIDTH - xy[rows, :, 1]
        positions = Positions(slots=positions.slots, xy=xy)
    return replace(match, events=events, positions=positions)


def to_spadl_frame(match: Match, *, left_to_right: bool = False) -> pd.DataFrame:
    """The match's events as a validated SPADL frame.

    Args:
        match: The match to convert.
        left_to_right: Mirror the away team's actions so every action attacks towards x = 105.

    Returns:
        A frame with exactly the SPADL columns, one row per event.
    """
    if left_to_right:
        match = to_left_to_right(match)
    frame = pd.DataFrame(
        {
            "game_id": [event.game_id for event in match.events],
            "original_event_id": [event.original_event_id for event in match.events],
            "action_id": [event.action_id for event in match.events],
            "period_id": [event.period_id for event in match.events],
            "time_seconds": [event.time_seconds for event in match.events],
            "team_id": [event.team_id for event in match.events],
            "player_id": [event.player_id for event in match.events],
            "start_x": [event.start_x for event in match.events],
            "start_y": [event.start_y for event in match.events],
            "end_x": [event.end_x for event in match.events],
            "end_y": [event.end_y for event in match.events],
            "type_id": [int(event.action_type) for event in match.events],
            "result_id": [int(event.result) for event in match.events],
            "bodypart_id": [int(event.bodypart) for event in match.events],
        },
    ).astype(
        {"time_seconds": float, "start_x": float, "start_y": float, "end_x": float, "end_y": float}
    )
    return pd.DataFrame(SPADLSchema.validate(frame))


def to_extension_frame(match: Match) -> pd.DataFrame:
    """The events' extension fields, keyed by ``(game_id, action_id)``."""
    return pd.DataFrame(
        {
            "game_id": [event.game_id for event in match.events],
            "action_id": [event.action_id for event in match.events],
            "possession_id": [event.possession_id for event in match.events],
            "phase": [event.phase.value for event in match.events],
            "planted_moment_id": pd.array(
                [event.planted_moment_id for event in match.events], dtype="Int64"
            ),
        },
    )


def to_snapshot_frame(match: Match, *, left_to_right: bool = False) -> pd.DataFrame:
    """Every known player position, one row per player per action.

    Args:
        match: The match to convert.
        left_to_right: Mirror the snapshots of away-team actions, matching `to_spadl_frame`.

    Returns:
        A frame with the snapshot columns. Unknown positions are left out, so a match without
        positions gives an empty frame.
    """
    if left_to_right:
        match = to_left_to_right(match)
    positions = match.positions
    if positions is None or not match.events:
        return pd.DataFrame(columns=pd.Index(SNAPSHOT_COLUMNS))

    n_actions, n_slots, _ = positions.xy.shape
    xy = positions.xy

    actors = np.array([event.player_id for event in match.events])
    slot_players = np.array([slot.player_id for slot in positions.slots])
    frame = pd.DataFrame(
        {
            "game_id": match.game_id,
            "action_id": np.repeat(np.arange(n_actions), n_slots),
            "player_id": np.tile(slot_players, n_actions),
            "team_id": np.tile([slot.team_id for slot in positions.slots], n_actions),
            "x": xy[:, :, 0].ravel(),
            "y": xy[:, :, 1].ravel(),
            "is_actor": (actors[:, None] == slot_players[None, :]).ravel(),
            "is_goalkeeper": np.tile([slot.is_goalkeeper for slot in positions.slots], n_actions),
        },
    )
    return frame.dropna(subset=["x", "y"]).reset_index(drop=True)


def events_from_frames(spadl: pd.DataFrame, extension: pd.DataFrame) -> tuple[Event, ...]:
    """Rebuild events from a SPADL frame and its extension frame.

    Both frames must be in the stored direction, not normalised left to right.
    """
    merged = spadl.merge(extension, on=["game_id", "action_id"], how="left", validate="1:1")
    return tuple(
        Event(
            game_id=GameId(int(row["game_id"])),
            action_id=ActionId(int(row["action_id"])),
            period_id=int(row["period_id"]),
            time_seconds=float(row["time_seconds"]),
            team_id=TeamId(int(row["team_id"])),
            player_id=PlayerId(int(row["player_id"])),
            start_x=float(row["start_x"]),
            start_y=float(row["start_y"]),
            end_x=float(row["end_x"]),
            end_y=float(row["end_y"]),
            action_type=ActionType(int(row["type_id"])),
            result=Result(int(row["result_id"])),
            bodypart=BodyPart(int(row["bodypart_id"])),
            possession_id=int(row["possession_id"]),
            phase=Phase(row["phase"]),
            planted_moment_id=None
            if pd.isna(row["planted_moment_id"])
            else int(row["planted_moment_id"]),
        )
        for row in merged.to_dict("records")
    )


def positions_from_snapshot_frame(snapshots: pd.DataFrame, n_actions: int) -> Positions:
    """Rebuild a match's position array from its snapshot frame.

    Players get slots in the order they first appear in the frame. Positions missing from
    the frame become NaN.
    """
    players = snapshots.drop_duplicates("player_id")
    slots = tuple(
        PlayerSlot(
            PlayerId(int(row["player_id"])), TeamId(int(row["team_id"])), bool(row["is_goalkeeper"])
        )
        for row in players.to_dict("records")
    )
    slot_index = {slot.player_id: index for index, slot in enumerate(slots)}
    xy = np.full((n_actions, len(slots), 2), np.nan)
    columns = snapshots.player_id.map(slot_index).to_numpy()
    rows = snapshots.action_id.to_numpy()
    xy[rows, columns, 0] = snapshots.x.to_numpy()
    xy[rows, columns, 1] = snapshots.y.to_numpy()
    return Positions(slots=slots, xy=xy)
