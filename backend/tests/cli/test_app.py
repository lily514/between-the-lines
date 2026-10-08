from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from btl.cli.app import app
from btl.cli.render import PITCH_LEGEND
from btl.io import load_match, load_threat_model
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

    shown = runner.invoke(
        app,
        ["events", str(tmp_path / "match-0007"), "--count", "3", "--model", str(tmp_path / "none")],
        env=WIDE,
    )

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


def test_fit_xt_saves_a_model_that_events_uses_for_a_threat_column(tmp_path: Path) -> None:
    model = tmp_path / "expected-threat.json"
    runner.invoke(app, ["simulate", "--seed", "7", "--out", str(tmp_path)], env=WIDE)

    fitted = runner.invoke(
        app, ["fit-xt", "--matches", "3", "--seed", "1", "--out", str(model)], env=WIDE
    )

    assert fitted.exit_code == 0, fitted.output
    assert "Fitted on 3 matches" in fitted.output
    assert load_threat_model(model).fitted_on.seed == 1
    shown = runner.invoke(
        app, ["events", str(tmp_path / "match-0007"), "--model", str(model)], env=WIDE
    )
    assert shown.exit_code == 0, shown.output
    assert "threat" in shown.output


def test_events_without_a_model_says_how_to_get_threat_values(tmp_path: Path) -> None:
    runner.invoke(app, ["simulate", "--seed", "7", "--out", str(tmp_path)], env=WIDE)

    shown = runner.invoke(
        app,
        ["events", str(tmp_path / "match-0007"), "--model", str(tmp_path / "missing.json")],
        env=WIDE,
    )

    assert shown.exit_code == 0, shown.output
    assert "run `btl fit-xt`" in shown.output


def test_tags_lists_the_concepts_found_in_a_saved_match(tmp_path: Path) -> None:
    runner.invoke(app, ["simulate", "--seed", "7", "--out", str(tmp_path)], env=WIDE)

    shown = runner.invoke(app, ["tags", str(tmp_path / "match-0007")], env=WIDE)

    assert shown.exit_code == 0, shown.output
    assert "switch of play" in shown.output
    assert "tags: " in shown.output


def test_tags_can_show_one_concept_and_rejects_unknown_ones(tmp_path: Path) -> None:
    runner.invoke(app, ["simulate", "--seed", "7", "--out", str(tmp_path)], env=WIDE)
    match_dir = str(tmp_path / "match-0007")

    one = runner.invoke(app, ["tags", match_dir, "--concept", "switch_of_play"], env=WIDE)
    unknown = runner.invoke(app, ["tags", match_dir, "--concept", "nutmeg"], env=WIDE)

    assert one.exit_code == 0, one.output
    assert unknown.exit_code == 2


def test_simulate_plants_moments_that_moments_shows(tmp_path: Path) -> None:
    simulated = runner.invoke(
        app,
        ["simulate", "--seed", "7", "--out", str(tmp_path), "--plant", "line_breaking_pass:1,2,3"],
        env=WIDE,
    )

    assert simulated.exit_code == 0, simulated.output
    assert "3 planted moments" in simulated.output
    match, _ = load_match(tmp_path / "match-0007")
    assert [moment.difficulty for moment in match.planted] == [1, 2, 3]

    shown = runner.invoke(app, ["moments", str(tmp_path / "match-0007")], env=WIDE)

    assert shown.exit_code == 0, shown.output
    for level in (1, 2, 3):
        assert f"Moment {level} · line breaking pass · level {level}" in shown.output
    assert shown.output.count("Detector: line breaking pass") == 3
    assert shown.output.count(PITCH_LEGEND) == 3


def test_simulate_explains_a_moment_it_cannot_plant(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["simulate", "--seed", "7", "--out", str(tmp_path), "--plant", "switch_of_play:1"],
        env=WIDE,
    )

    assert result.exit_code == 2
    assert "can't be planted yet" in result.output


def test_moments_says_when_a_match_has_none(tmp_path: Path) -> None:
    runner.invoke(app, ["simulate", "--seed", "7", "--out", str(tmp_path)], env=WIDE)

    shown = runner.invoke(app, ["moments", str(tmp_path / "match-0007")], env=WIDE)

    assert shown.exit_code == 0, shown.output
    assert "No planted moments" in shown.output


def test_moments_shows_a_counter_press_from_just_after_the_ball_is_lost(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["simulate", "--seed", "7", "--out", str(tmp_path), "--plant", "counter_press:2"],
        env=WIDE,
    )

    shown = runner.invoke(app, ["moments", str(tmp_path / "match-0007")], env=WIDE)

    assert shown.exit_code == 0, shown.output
    match, _ = load_match(tmp_path / "match-0007")
    (moment,) = match.planted
    assert f"the pitch at #{moment.pause_action_id + 1}" in shown.output
    assert "Detector: counter press · seconds to win back" in shown.output
    assert "None" not in shown.output
