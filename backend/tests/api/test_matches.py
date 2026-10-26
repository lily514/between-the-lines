from typing import Any

from fastapi.testclient import TestClient

from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import SEED, answer, client, next_step, started


def matches(api: TestClient, viewer_id: str = "demo") -> list[dict[str, Any]]:
    response = api.get(f"/api/viewers/{viewer_id}/matches")
    assert response.status_code == 200, response.text
    return response.json()


def test_a_new_viewer_sees_three_upcoming_matches_with_dates_and_nothing_else() -> None:
    api = client(MemoryLearnerStore())
    status = started(api)

    listed = matches(api)

    assert [m["match_number"] for m in listed] == [1, 2, 3]
    assert [m["date"] for m in listed] == ["2026-10-24", "2026-10-31", "2026-11-07"]
    assert listed[0]["date_label"] == "Sat 24 Oct"
    assert {m["kick_off"] for m in listed} == {"15:00"}
    assert {m["state"] for m in listed} == {"upcoming"}
    assert all(m["score"] is None and m["your_result"] is None for m in listed)
    assert listed[0]["home"] == status["fixture"]["home"]


def test_after_one_answer_the_match_is_in_progress_with_the_score_so_far() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    question = next_step(api)
    answer(api, question["pack_id"], question["options"][0]["key"])

    first = matches(api)[0]

    assert first["state"] == "in_progress"
    assert first["questions"] == 1
    assert first["score"]["clock"] is not None
    assert first["your_result"] is None


def test_a_finished_match_gives_the_full_time_score_and_your_result() -> None:
    api = client(MemoryLearnerStore())
    api.post("/api/viewers", json={"viewer_id": "fan", "seed": SEED, "club": 4})
    while (step := next_step(api, "fan"))["kind"] == "question":
        answer(api, step["pack_id"], step["options"][0]["key"], "fan")

    first, second, _ = matches(api, "fan")

    assert first["state"] == "finished"
    assert first["score"] == {
        "home": step["home_goals"],
        "away": step["away_goals"],
        "clock": None,
    }
    assert first["your_result"] == step["your_result"] is not None
    assert first["questions"] == step["questions"]
    assert second["state"] == "upcoming"


def test_an_unknown_viewer_has_no_matches() -> None:
    api = client(MemoryLearnerStore())

    assert api.get("/api/viewers/nobody/matches").status_code == 404
