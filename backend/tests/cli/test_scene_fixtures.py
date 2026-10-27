"""The page's scene fixtures: one real moment per active concept, committed and kept fresh."""

import json
from functools import cache
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from btl.cli.app import app
from btl.learn.concept_map import ConceptKey, load_concept_map
from btl.learn.questions import active_concepts
from btl.learn.scenes import FIXTURE_SEED, fixture_course, scene_fixtures, to_text

FIXTURES = Path(__file__).parents[3] / "frontend" / "src" / "scenes" / "fixtures"
REFRESH = (
    "frontend/src/scenes/fixtures is out of date. From backend/ run `uv run btl scene-fixtures`."
)
runner = CliRunner()


@cache
def built() -> dict[str, dict[str, Any]]:
    return {str(key): fixture for key, fixture in scene_fixtures(fixture_course()).items()}


def committed(key: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES / f"{key}.json").read_text(encoding="utf-8")))


def test_there_is_one_fixture_per_active_concept_and_no_other() -> None:
    active = [str(key) for key in active_concepts(load_concept_map())]

    assert sorted(path.stem for path in FIXTURES.glob("*.json")) == sorted(active)
    assert list(built()) == active


def test_the_committed_fixtures_are_what_the_command_writes() -> None:
    for key, fixture in built().items():
        assert (FIXTURES / f"{key}.json").read_text(encoding="utf-8") == to_text(fixture), REFRESH


def test_every_fixture_fills_its_concepts_evidence_fields_and_times_its_path() -> None:
    concept_map = load_concept_map()
    for key, fixture in built().items():
        concept = concept_map.concept(ConceptKey(key))
        pack = fixture["pack"]
        facts = set(pack["context"]) | set(pack["outcome"])
        assert set(concept.evidence_fields) <= facts, key
        assert fixture["evidence_fields"] == list(concept.evidence_fields)
        assert fixture["concept"] == key and fixture["name"] == concept.name
        assert fixture["match"]["seed"] in {FIXTURE_SEED * 1000 + n for n in (1, 2, 3)}
        # The snapshot at the key frame: both full teams, one on the ball.
        markers = fixture["snapshot"]["markers"]
        assert len(markers) == 22
        assert [m["role"] for m in markers].count("on the ball") == 1
        assert fixture["snapshot"]["action_id"] == pack["picture"]["action_id"]
        # The path runs the moment's span, in time order, and ends where the ball arrives.
        path = fixture["path"]
        assert [p["action_id"] for p in path[:-1]] == list(
            range(fixture["moment"]["span"][0], fixture["moment"]["span"][1] + 1)
        )
        assert path[0]["at"] == 0 and path[-1]["action"] == "end"
        assert [p["at"] for p in path] == sorted(p["at"] for p in path)
        assert [[p["x"], p["y"]] for p in path] == [list(point) for point in pack["reveal_path"]]
        # Every level's question is worded, with three options.
        assert set(fixture["questions"]) <= {"1", "2", "3"} and "1" in fixture["questions"]
        for question in fixture["questions"].values():
            assert "{" not in question["text"] and len(question["options"]) == 3
            assert question["correct"] in ("A", "B", "C")


def test_the_chosen_moments_tell_each_concepts_story() -> None:
    assert built()["offside"]["moment"]["evidence"]["offside"] == 1.0
    assert built()["restarts"]["moment"]["evidence"]["over a goal line"] == 1.0
    assert built()["fouls_and_cards"]["moment"]["evidence"]["advantage"] == 0.0
    assert 35 <= built()["tackles"]["moment"]["evidence"]["metres from own goal"] < 70
    assert built()["transitions"]["moment"]["evidence"]["won (m from own goal)"] >= 20
    assert list(built()["transitions"]["pack"]["picture"]["path"]) == []
    assert committed("transitions")["pack"]["picture"]["path"] == []


def test_the_command_writes_the_files_where_asked(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scene-fixtures", "--out", str(tmp_path)], env={"COLUMNS": "200"})

    assert result.exit_code == 0, result.output
    assert "Wrote 8 scene fixtures" in result.output
    assert committed("tackles") == json.loads((tmp_path / "tackles.json").read_text())
