from typing import Any

from fastapi.testclient import TestClient

from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import answer, client, next_step, started


def get_report(api: TestClient, number: int, at: str) -> Any:
    return api.get(f"/api/viewers/demo/matches/{number}/report", params={"at": at})


def play_match(api: TestClient) -> dict[str, Any]:
    while (step := next_step(api))["kind"] == "question":
        answer(api, step["pack_id"], step["options"][0]["key"])
    return step


def test_no_report_before_its_break() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    assert get_report(api, 1, "halftime").status_code == 409
    assert get_report(api, 1, "full_time").status_code == 409
    assert get_report(api, 2, "halftime").status_code == 409
    assert get_report(api, 4, "halftime").status_code == 404
    assert get_report(api, 1, "kickoff").status_code == 422


def test_the_halftime_report_opens_once_the_next_question_is_in_the_second_half() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    while (step := next_step(api))["kind"] == "question" and step["delivered"]["period"] == 1:
        assert get_report(api, 1, "halftime").status_code == 409
        answer(api, step["pack_id"], step["options"][0]["key"])

    response = get_report(api, 1, "halftime")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["at"] == "halftime"
    assert body["your_result"] is None


def test_after_full_time_both_reports_agree_with_the_summary() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    full_time = play_match(api)

    half = get_report(api, 1, "halftime").json()
    whole = get_report(api, 1, "full_time").json()

    assert (whole["home_goals"], whole["away_goals"]) == (
        full_time["home_goals"],
        full_time["away_goals"],
    )
    assert len(whole["answers"]) == full_time["questions"]
    assert whole["right"] == sum(line["correct"] for line in whole["answers"])
    assert {c["name"]: c["after"] for c in whole["concepts"]} == {
        c["name"]: c["after"] for c in full_time["concepts"]
    }
    assert len(half["answers"]) <= len(whole["answers"])
    assert half["home_goals"] <= whole["home_goals"]
    chances = next(s for s in whole["strands"] if s["key"] == "chances")
    assert chances["now"] is not None and chances["concepts"] == 1
    assert whole["note"]
    # The level rows lock the same concepts the map does, and the summary's moves carry a level.
    status = api.get("/api/viewers/demo").json()
    assert {c["key"]: c["waits_for"] for c in whole["concepts"]} == {
        bar["key"]: bar["waits_for"] for bar in status["concepts"]
    }
    assert {c["name"]: (c["level"], c["band"], c["mastered"]) for c in full_time["concepts"]} == {
        bar["name"]: (bar["level"], bar["band"], bar["value"] >= 0.95) for bar in status["concepts"]
    }
