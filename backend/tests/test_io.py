import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from btl.io import (
    META_FILE,
    POSITIONS_FILE,
    MatchInfo,
    load_match,
    load_threat_model,
    save_match,
    save_threat_model,
)
from btl.league.league import generate_league
from btl.schema.ids import GameId
from btl.sim.engine import simulate_match
from btl.value.xt import FitInfo, ThreatModel
from tests.fixtures.matches import six_event_match

INFO = MatchInfo(seed=7, league_seed=0, home_formation="4-4-2", away_formation="4-3-3")
MODEL = ThreatModel(
    grid=tuple(tuple(0.001 * (row + column) for column in range(16)) for row in range(12)),
    fitted_on=FitInfo(matches=3, seed=1, league_seed=0, actions=4_812),
)


def test_a_saved_match_loads_back_unchanged(tmp_path: Path) -> None:
    match = six_event_match()

    directory = save_match(match, INFO, tmp_path)

    assert directory == tmp_path / "match-0001"
    assert load_match(directory) == (match, INFO)


def test_a_simulated_match_loads_back_unchanged(tmp_path: Path) -> None:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    match = simulate_match(home, away, 7)

    assert load_match(save_match(match, INFO, tmp_path)) == (match, INFO)


def test_a_match_without_positions_loads_back_without_them(tmp_path: Path) -> None:
    match = replace(six_event_match(), positions=None)

    directory = save_match(match, INFO, tmp_path)

    assert not (directory / POSITIONS_FILE).exists()
    assert load_match(directory)[0] == match


def test_saving_again_without_positions_removes_the_old_ones(tmp_path: Path) -> None:
    save_match(six_event_match(), INFO, tmp_path)

    directory = save_match(replace(six_event_match(), positions=None), INFO, tmp_path)

    assert load_match(directory)[0].positions is None


def test_each_match_gets_its_own_directory(tmp_path: Path) -> None:
    first = save_match(six_event_match(), INFO, tmp_path)
    other_game = six_event_match()
    other_game = replace(
        other_game,
        game_id=GameId(12),
        events=tuple(replace(event, game_id=GameId(12)) for event in other_game.events),
    )

    second = save_match(other_game, INFO, tmp_path)

    assert second == tmp_path / "match-0012"
    assert first != second


def test_a_match_saved_with_another_schema_version_is_refused(tmp_path: Path) -> None:
    directory = save_match(six_event_match(), INFO, tmp_path)
    meta = json.loads((directory / META_FILE).read_text())
    (directory / META_FILE).write_text(json.dumps({**meta, "schema_version": 0}))

    with pytest.raises(ValueError, match="schema version 0"):
        load_match(directory)


def test_loading_a_folder_with_no_match_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_match(tmp_path)


def test_a_saved_threat_model_loads_back_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "models" / "expected-threat.json"

    save_threat_model(MODEL, path)

    assert load_threat_model(path) == MODEL


def test_saving_the_same_threat_model_gives_the_same_file(tmp_path: Path) -> None:
    save_threat_model(MODEL, tmp_path / "first.json")
    save_threat_model(MODEL, tmp_path / "second.json")

    assert (tmp_path / "first.json").read_bytes() == (tmp_path / "second.json").read_bytes()


def test_a_threat_model_in_another_format_version_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "expected-threat.json"
    save_threat_model(MODEL, path)
    path.write_text(json.dumps({**json.loads(path.read_text()), "format_version": 0}))

    with pytest.raises(ValueError, match="format version 0"):
        load_threat_model(path)
