from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from btl.cli.app import app
from btl.io import load_match
from btl.league.league import generate_league

runner = CliRunner()
WIDE = {"COLUMNS": "200"}


def test_help_describes_the_tool() -> None:
    result = runner.invoke(app, ["--help"], env=WIDE)

    assert result.exit_code == 0
    assert "synthetic football matches" in result.output


def test_simulate_saves_a_match_that_events_can_show(tmp_path: Path) -> None:
    simulated = runner.invoke(app, ["simulate", "--seed", "7", "--out", str(tmp_path)], env=WIDE)

    assert simulated.exit_code == 0, simulated.output
    assert f"saved to {tmp_path / 'match-0007'}" in simulated.output
    match, info = load_match(tmp_path / "match-0007")
    assert info.seed == 7

    shown = runner.invoke(app, ["events", str(tmp_path / "match-0007"), "--count", "3"], env=WIDE)

    assert shown.exit_code == 0, shown.output
    assert f"Events 0 to 2 of {len(match.events):,}" in shown.output


def test_simulate_can_pick_the_clubs_in_any_case(tmp_path: Path) -> None:
    home, away = generate_league(np.random.default_rng(0)).clubs[3:5]

    result = runner.invoke(
        app,
        [
            "simulate",
            "--seed",
            "1",
            "--out",
            str(tmp_path),
            "--home",
            home.short_name.lower(),
            "--away",
            away.short_name,
        ],
        env=WIDE,
    )

    assert result.exit_code == 0, result.output
    match, _ = load_match(tmp_path / "match-0001")
    assert (match.home_team_id, match.away_team_id) == (home.team_id, away.team_id)


def test_simulate_rejects_an_unknown_club(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["simulate", "--seed", "1", "--home", "XXX", "--away", "YYY", "--out", str(tmp_path)],
        env=WIDE,
    )

    assert result.exit_code == 2
    assert "no club 'XXX'" in result.output


def test_events_explains_a_folder_with_no_match(tmp_path: Path) -> None:
    result = runner.invoke(app, ["events", str(tmp_path)], env=WIDE)

    assert result.exit_code == 2
    assert "no saved match" in result.output
