# pyright: basic
# pandas is only partially typed; see CLAUDE.md on edge modules.
"""Saving and loading matches: one directory per match, with parquet tables and a JSON summary.

A saved match looks like this:

    match-0007/
    ├── meta.json          # schema version, ids, and how the match was made
    ├── events.parquet     # one row per event: SPADL columns, then our extension columns
    └── positions.parquet  # one row per player per event; absent if the match has no positions

The files are a convenience. Any simulated match can be regenerated from the seeds in
``meta.json``.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from btl.schema.frames import (
    EXTENSION_COLUMNS,
    SPADL_COLUMNS,
    events_from_frames,
    positions_from_snapshot_frame,
    to_extension_frame,
    to_snapshot_frame,
    to_spadl_frame,
)
from btl.schema.ids import GameId, TeamId
from btl.schema.match import Match

# Bump whenever the saved layout or columns change, so old files fail loudly.
SCHEMA_VERSION = 1
META_FILE = "meta.json"
EVENTS_FILE = "events.parquet"
POSITIONS_FILE = "positions.parquet"


@dataclass(frozen=True, slots=True)
class MatchInfo:
    """How a simulated match was made: enough to regenerate it and to name its clubs and players."""

    seed: int
    league_seed: int
    home_formation: str
    away_formation: str


def match_directory_name(game_id: GameId) -> str:
    """The directory a match is saved in, e.g. ``match-0007``."""
    return f"match-{game_id:04d}"


def save_match(match: Match, info: MatchInfo, parent: Path) -> Path:
    """Save a match into a new directory under ``parent``, replacing any earlier save of it.

    Returns:
        The match's directory.
    """
    directory = parent / match_directory_name(match.game_id)
    directory.mkdir(parents=True, exist_ok=True)
    events = to_spadl_frame(match).merge(
        to_extension_frame(match), on=["game_id", "action_id"], validate="1:1"
    )
    events.to_parquet(directory / EVENTS_FILE, index=False)
    positions_path = directory / POSITIONS_FILE
    if match.positions is None:
        positions_path.unlink(missing_ok=True)
    else:
        to_snapshot_frame(match).to_parquet(positions_path, index=False)
    meta = {
        "schema_version": SCHEMA_VERSION,
        "game_id": match.game_id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        **asdict(info),
    }
    (directory / META_FILE).write_text(json.dumps(meta, indent=2) + "\n")
    return directory


def load_match(directory: Path) -> tuple[Match, MatchInfo]:
    """Load a match saved by `save_match`.

    Raises:
        FileNotFoundError: If the directory has no saved match.
        ValueError: If the match was saved with a different schema version.
    """
    meta = json.loads((directory / META_FILE).read_text())
    if meta["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"{directory} was saved with schema version {meta['schema_version']}, "
            f"but this version of btl reads version {SCHEMA_VERSION}"
        )
    events_frame = pd.read_parquet(directory / EVENTS_FILE)
    events = events_from_frames(
        events_frame.reindex(columns=SPADL_COLUMNS), events_frame.reindex(columns=EXTENSION_COLUMNS)
    )
    positions_path = directory / POSITIONS_FILE
    positions = (
        positions_from_snapshot_frame(pd.read_parquet(positions_path), len(events))
        if positions_path.exists()
        else None
    )
    match = Match(
        game_id=GameId(meta["game_id"]),
        home_team_id=TeamId(meta["home_team_id"]),
        away_team_id=TeamId(meta["away_team_id"]),
        events=events,
        positions=positions,
    )
    info = MatchInfo(
        seed=meta["seed"],
        league_seed=meta["league_seed"],
        home_formation=meta["home_formation"],
        away_formation=meta["away_formation"],
    )
    return match, info
