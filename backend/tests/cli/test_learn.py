import json
from pathlib import Path

from typer.testing import CliRunner

from btl.cli.app import app
from btl.io import save_threat_model
from tests.fixtures.learning import threat_model

runner = CliRunner()
WIDE = {"COLUMNS": "200"}


def saved_model(folder: Path) -> Path:
    path = folder / "model.json"
    save_threat_model(threat_model(), path)
    return path


def learn(tmp_path: Path, *extra: str, answers: str = "A\n" * 30) -> str:
    result = runner.invoke(
        app,
        [
            "learn",
            "--viewer",
            "lily",
            "--learners",
            str(tmp_path / "learners"),
            "--model",
            str(saved_model(tmp_path)),
            *extra,
        ],
        input=answers,
        env=WIDE,
    )
    assert result.exit_code == 0, result.output
    return result.output


def test_learn_plays_one_match_and_saves_every_answer(tmp_path: Path) -> None:
    output = learn(tmp_path)

    saved = json.loads((tmp_path / "learners" / "lily.json").read_text())
    assert "Match 1:" in output and "Your answer (A, B, C)" in output
    assert "questions this match" in output
    assert "again for match 2" in output
    assert saved["match_number"] == 2 and len(saved["attempts"]) >= 2


def test_learn_carries_on_with_the_next_match_and_can_start_again(tmp_path: Path) -> None:
    learn(tmp_path)

    second = learn(tmp_path)
    again = learn(tmp_path, "--reset")

    assert "Match 2:" in second
    assert "Match 1:" in again


def test_learn_explains_each_question_and_how_the_bars_moved(tmp_path: Path) -> None:
    output = learn(tmp_path)

    assert "Right read." in output or "Good instinct, not this one." in output
    assert "Takeaway:" in output
    assert "sure you understand it" in output
    assert "Line-breaking passes" in output and "Counter-pressing" in output


def test_learn_asks_again_until_the_answer_is_an_option(tmp_path: Path) -> None:
    output = learn(tmp_path, answers="X\n" + "b\n" * 30)

    assert "Please type one of A, B, C." in output


def test_learn_refuses_a_viewer_name_that_is_not_plain(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["learn", "--viewer", "../x", "--learners", str(tmp_path)], env=WIDE
    )

    assert result.exit_code != 0
    assert "isn't a valid viewer id" in result.output


def test_the_demo_viewer_watches_three_matches(tmp_path: Path) -> None:
    result = runner.invoke(app, ["demo-viewer", "--model", str(saved_model(tmp_path))], env=WIDE)

    assert result.exit_code == 0, result.output
    for number in (1, 2, 3):
        assert f"Match {number}:" in result.output
    assert "The demo viewer picks" in result.output
    assert "After three matches" in result.output


def test_learn_with_a_club_watches_its_fixtures_and_keeps_it(tmp_path: Path) -> None:
    first = learn(tmp_path, "--club", "hex")
    second = learn(tmp_path)

    saved = json.loads((tmp_path / "learners" / "lily.json").read_text())
    assert "Your team: Hexham Anchors" in first and "Your team: Hexham Anchors" in second
    assert "Hexham Anchors" in first.split("Match 1:")[1].splitlines()[0]
    assert saved["club"] == 2


def test_learn_refuses_an_unknown_club_or_a_change_after_answering(tmp_path: Path) -> None:
    model = str(saved_model(tmp_path))
    base = ["learn", "--viewer", "lily", "--learners", str(tmp_path / "learners")]
    unknown = runner.invoke(app, [*base, "--model", model, "--club", "nowhere"], env=WIDE)
    learn(tmp_path, "--club", "HEX")
    changed = runner.invoke(app, [*base, "--model", model, "--club", "RIP"], env=WIDE)

    assert unknown.exit_code != 0 and "no club called 'nowhere'" in unknown.output
    assert changed.exit_code != 0 and "team can't change" in changed.output


def test_learn_shows_both_elevens_before_the_match(tmp_path: Path) -> None:
    output = learn(tmp_path, "--club", "LUD")

    sheet = output.split("Match 1:")[1].split("+---")[0]
    assert "Ludlow Ferrymen · " in sheet and "your team" in sheet
    assert sheet.count("Goalkeeper") == 2 and "Left back" in sheet
