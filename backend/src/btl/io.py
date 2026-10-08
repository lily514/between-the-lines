# pyright: basic
# pandas is only partially typed; see CLAUDE.md on edge modules.
"""Saving and loading matches and Expected Threat models.

A match gets one directory, with parquet tables and a JSON summary:

    match-0007/
    ├── meta.json          # schema version, ids, how the match was made, planted moments
    ├── events.parquet     # one row per event: SPADL columns, then our extension columns
    └── positions.parquet  # one row per player per event; absent if the match has no positions

A threat model is one JSON file: the grid, plus the matches and seeds it was fitted on.

The files are a convenience. Any simulated match can be regenerated from the seeds in
``meta.json``, and any model refitted from the seeds in its file.
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
from btl.schema.ids import ActionId, GameId, TeamId
from btl.schema.match import Match
from btl.schema.moment import PlantedMoment
from btl.schema.vocab import ConceptId
from btl.value.xt import FitInfo, ThreatModel

# Bump whenever the saved layout or columns change, so old files fail loudly.
SCHEMA_VERSION = 2
META_FILE = "meta.json"
EVENTS_FILE = "events.parquet"
POSITIONS_FILE = "positions.parquet"
# Bump whenever the threat model file's layout changes.
THREAT_MODEL_VERSION = 1


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
        "planted": [asdict(moment) for moment in match.planted],
    }
    (directory / META_FILE).write_text(json.dumps(meta, indent=2) + "\n")
    return directory


def saved_match_directories(parent: Path) -> list[Path]:
    """The directories directly under ``parent`` that hold a saved match, sorted by name.

    A missing ``parent`` has none.
    """
    if not parent.is_dir():
        return []
    return sorted(path.parent for path in parent.glob(f"*/{META_FILE}"))


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
        planted=tuple(
            PlantedMoment(
                concept=ConceptId(moment["concept"]),
                difficulty=moment["difficulty"],
                pause_action_id=ActionId(moment["pause_action_id"]),
                answer_action_id=ActionId(moment["answer_action_id"]),
            )
            for moment in meta["planted"]
        ),
    )
    info = MatchInfo(
        seed=meta["seed"],
        league_seed=meta["league_seed"],
        home_formation=meta["home_formation"],
        away_formation=meta["away_formation"],
    )
    return match, info


def save_threat_model(model: ThreatModel, path: Path) -> None:
    """Save a threat model as JSON, creating its folder if needed.

    The same model always gives the same bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {
        "format_version": THREAT_MODEL_VERSION,
        "fitted_on": asdict(model.fitted_on),
        "grid": [list(row) for row in model.grid],
    }
    path.write_text(json.dumps(content, indent=2) + "\n")


def load_threat_model(path: Path) -> ThreatModel:
    """Load a threat model saved by `save_threat_model`.

    Raises:
        FileNotFoundError: If there is no file at ``path``.
        ValueError: If the model was saved in a different format version.
    """
    content = json.loads(path.read_text())
    if content["format_version"] != THREAT_MODEL_VERSION:
        raise ValueError(
            f"{path} was saved in format version {content['format_version']}, "
            f"but this version of btl reads version {THREAT_MODEL_VERSION}"
        )
    grid = tuple(tuple(float(value) for value in row) for row in content["grid"])
    return ThreatModel(grid, FitInfo(**content["fitted_on"]))
