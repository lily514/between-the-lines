from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import answer, client, next_step, started


def test_with_questions_off_the_match_goes_straight_to_full_time_and_still_has_a_report() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    status = api.put("/api/viewers/demo/pace", json={"pace": "off"}).json()
    step = next_step(api)

    assert (status["pace"], status["pace_next"]) == ("off", None)
    assert step["kind"] == "full_time"
    assert step["questions"] == 0
    report = api.get("/api/viewers/demo/matches/1/report", params={"at": "full_time"})
    assert report.status_code == 200
    assert report.json()["answers"] == []


def test_a_change_part_way_through_a_match_waits_for_the_next() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    question = next_step(api)
    answer(api, question["pack_id"], question["options"][0]["key"])

    status = api.put("/api/viewers/demo/pace", json={"pace": "rarely"}).json()

    assert (status["pace"], status["pace_next"]) == ("normal", "rarely")


def test_an_unknown_pace_is_refused() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    assert api.put("/api/viewers/demo/pace", json={"pace": "sometimes"}).status_code == 422
