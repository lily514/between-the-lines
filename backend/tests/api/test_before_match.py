"""The flows before a match: First looks for new concepts, Level-ups after a match, the levels."""

from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient

from btl.learn.learner import LearnerState
from btl.learn.levels import band_for, band_rose
from btl.learn.team_sheet import STAGE_OPENED, sheet_stage
from btl.store.base import INTRODUCED_BEFORE_VERSION_4
from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import SEED, answer, client, course, demo_attempts, next_step, started

NEW_IN_M5 = ["tackles", "shots_and_goals", "transitions"]


def before_match(api: TestClient, viewer_id: str = "demo") -> dict[str, Any]:
    response = api.get(f"/api/viewers/{viewer_id}/before-match")
    assert response.status_code == 200, response.text
    return response.json()


def test_a_new_viewer_has_no_first_looks_or_level_ups_only_their_levels() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    body = before_match(api)

    assert body["match_number"] == 1
    assert body["first_looks"] == [] and body["level_ups"] == []
    assert body["unlock_note"] is None
    assert [row["key"] for row in body["levels"]] == list(course().active)
    assert {row["level"] for row in body["levels"]} == {"Getting there"}
    assert {row["band"] for row in body["levels"]} == {"getting_there"}
    assert all(row["moved"] is False for row in body["levels"])
    by_key = {row["key"]: row for row in body["levels"]}
    assert by_key["transitions"]["waits_for"] == ["Tackles and turnovers", "Restarts"]
    assert by_key["counter_press"]["waits_for"] == ["Tackles and turnovers"]
    assert by_key["restarts"]["waits_for"] == []
    assert by_key["restarts"]["strand_name"] == "Game flow"


def test_a_viewer_from_before_milestone_5_gets_a_first_look_at_exactly_the_new_concepts() -> None:
    store = MemoryLearnerStore()
    store.create(LearnerState("old", SEED, introduced=INTRODUCED_BEFORE_VERSION_4))
    api = client(store)

    body = before_match(api, "old")

    assert [row["key"] for row in body["first_looks"]] == NEW_IN_M5
    assert {row["level"] for row in body["first_looks"]} == {"Getting there"}
    assert body["level_ups"] == []


def test_finishing_the_first_look_marks_the_concepts_introduced() -> None:
    store = MemoryLearnerStore()
    store.create(LearnerState("old", SEED, introduced=INTRODUCED_BEFORE_VERSION_4))
    api = client(store)

    response = api.post("/api/viewers/old/introduced", json={"concepts": NEW_IN_M5[:2]})

    assert response.status_code == 200, response.text
    assert response.json()["viewer_id"] == "old"
    assert [row["key"] for row in before_match(api, "old")["first_looks"]] == ["transitions"]
    stored = store.get("old")
    assert stored is not None
    assert stored.state.introduced == (*INTRODUCED_BEFORE_VERSION_4, "tackles", "shots_and_goals")
    again = api.post("/api/viewers/old/introduced", json={"concepts": NEW_IN_M5[:2]})
    assert again.status_code == 200 and store.get("old") == stored


def test_only_concepts_asked_about_now_can_be_introduced() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    refused = api.post("/api/viewers/demo/introduced", json={"concepts": ["pressing"]})

    assert refused.status_code == 422 and "pressing" in refused.json()["detail"]
    assert api.post("/api/viewers/nobody/introduced", json={"concepts": []}).status_code == 404


def test_level_ups_are_the_concepts_whose_band_rose_over_the_last_match() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    expected = list(demo_attempts())
    while (step := next_step(api))["kind"] == "question":
        assert answer(api, step["pack_id"], expected.pop(0).chosen).status_code == 200
    report = api.get("/api/viewers/demo/matches/1/report", params={"at": "full_time"}).json()

    body = before_match(api)

    assert body["match_number"] == 2
    rose = [c for c in report["concepts"] if band_rose(c["before"], c["after"])]
    assert rose, "the demo viewer's first match should raise at least one band"
    assert [up["key"] for up in body["level_ups"]] == [c["key"] for c in rose]
    for up, move in zip(body["level_ups"], rose, strict=True):
        assert (up["before"], up["after"]) == (move["before"], move["after"])
        assert (up["band_before"], up["band"]) == (move["band_before"], move["band"])
        assert up["band"] == band_for(move["after"]).value
        assert up["level"] == move["level"] and up["strand_name"]
    moved = {row["key"] for row in body["levels"] if row["moved"]}
    assert moved == {up["key"] for up in body["level_ups"]}
    assert body["first_looks"] == []


def test_the_unlock_note_says_what_the_team_sheet_newly_shows() -> None:
    attempts = demo_attempts()
    in_first = tuple(a for a in attempts if a.match_number == 1)
    store = MemoryLearnerStore()
    store.create(
        replace(LearnerState("demo", SEED, attempts=in_first), match_number=2).with_introduced(
            course().active
        )
    )
    api = client(store)

    body = before_match(api)

    before = sheet_stage(course().mastery(LearnerState("demo", SEED)).values())
    after = sheet_stage(course().mastery(LearnerState("demo", SEED, attempts=in_first)).values())
    assert body["unlock_note"] == (STAGE_OPENED.get(after) if after > before else None)
    assert after >= before


def test_a_finished_viewer_has_nothing_before_a_match() -> None:
    store = MemoryLearnerStore()
    store.create(LearnerState("done", SEED, match_number=4))

    assert client(store).get("/api/viewers/done/before-match").status_code == 409
    assert client(store).get("/api/viewers/nobody/before-match").status_code == 404
