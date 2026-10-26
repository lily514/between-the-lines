from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from btl.api.app import create_app
from btl.learn.learner import MATCHES_PER_SESSION, Attempt, LearnerState
from btl.learn.session import Course, DemoViewer, start_session, watch_match
from btl.store.base import LearnerStore
from btl.store.json_files import JsonLearnerStore
from btl.store.memory import MemoryLearnerStore
from btl.tutor.templates import TemplateTutor
from tests.fixtures.learning import threat_model

NOW = "2026-10-08T12:00:00+00:00"
SEED = 7


@cache
def course() -> Course:
    return Course(threat_model(), TemplateTutor())


def client(store: LearnerStore, frontend: Path | None = None) -> TestClient:
    return TestClient(create_app(course, store, lambda: NOW, frontend))


@cache
def demo_attempts() -> tuple[Attempt, ...]:
    """What the scripted demo viewer answers over three matches, run in the terminal's way."""
    store = MemoryLearnerStore()
    start_session(store, "demo", SEED)
    viewer = DemoViewer()
    for _ in range(MATCHES_PER_SESSION):
        watch_match(course(), store, "demo", viewer, lambda: NOW)
    stored = store.get("demo")
    assert stored is not None
    return stored.state.attempts


def started(api: TestClient, viewer_id: str = "demo") -> dict[str, Any]:
    response = api.post("/api/viewers", json={"viewer_id": viewer_id, "seed": SEED})
    assert response.status_code == 200, response.text
    return response.json()


def next_step(api: TestClient, viewer_id: str = "demo") -> dict[str, Any]:
    response = api.post(f"/api/viewers/{viewer_id}/next")
    assert response.status_code == 200, response.text
    return response.json()


def answer(api: TestClient, pack_id: str, key: str, viewer_id: str = "demo") -> Any:
    return api.post(f"/api/viewers/{viewer_id}/answers", json={"pack_id": pack_id, "key": key})


def test_answering_through_the_api_gives_the_same_record_as_the_terminal() -> None:
    expected = list(demo_attempts())
    store = MemoryLearnerStore()
    api = client(store)
    started(api)
    full_times: list[dict[str, Any]] = []

    while len(full_times) < MATCHES_PER_SESSION:
        step = next_step(api)
        if step["kind"] == "full_time":
            full_times.append(step)
            continue
        attempt = expected[0]
        assert step["pack_id"] == attempt.pack_id
        response = answer(api, step["pack_id"], attempt.chosen)
        assert response.status_code == 200, response.text
        assert response.json()["correct"] is attempt.correct
        expected.pop(0)

    stored = store.get("demo")
    assert stored is not None
    assert [replace(a, answered_at="") for a in stored.state.attempts] == [
        replace(a, answered_at="") for a in demo_attempts()
    ]
    assert stored.state.finished
    assert [f["questions"] for f in full_times] == [
        sum(a.match_number == n for a in demo_attempts()) for n in (1, 2, 3)
    ]
    assert [f["next_match"] for f in full_times] == [2, 3, None]
    assert full_times[-1]["finished"] is True


def test_next_gives_the_same_question_until_it_is_answered() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    first, again = next_step(api), next_step(api)

    assert first == again
    assert first["kind"] == "question"
    assert {"key", "label", "neutral", "target_at"} == set(first["options"][0])


def test_the_feedback_shows_the_answer_the_evidence_and_how_mastery_moved() -> None:
    api = client(MemoryLearnerStore())
    status = started(api)
    question = next_step(api)

    feedback = answer(api, question["pack_id"], question["options"][0]["key"]).json()

    assert feedback["pack_id"] == question["pack_id"]
    assert feedback["verdict"] in {"Right read.", "Good instinct, not this one."}
    assert sum(option["correct"] for option in feedback["options"]) == 1
    assert [o["key"] for o in feedback["options"] if o["chosen"]] == [feedback["chosen"]]
    assert feedback["reveal_path"]
    before = {bar["name"]: bar["value"] for bar in status["concepts"]}
    assert {c["name"]: c["before"] for c in feedback["concepts"]} == before
    assert feedback["thresholds"] == status["thresholds"] == {"unlock": 0.8, "mastery": 0.95}
    assert feedback["match_seed"] == SEED * 1000 + 1


def test_a_wrong_answer_brings_a_common_mix_up_apart_from_the_explanation() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    told: list[dict[str, Any]] = []
    while not any(not f["correct"] for f in told):
        step = next_step(api)
        if step["kind"] == "question":
            told.append(answer(api, step["pack_id"], step["options"][0]["key"]).json())

    for feedback in told:
        assert (feedback["misconception"] is None) is feedback["correct"]
        assert "mix-up" not in feedback["explanation"]


def test_an_answer_to_another_question_is_refused_and_changes_nothing() -> None:
    store = MemoryLearnerStore()
    api = client(store)
    started(api)
    question = next_step(api)

    stale = answer(api, "0" * 16, question["options"][0]["key"])

    assert stale.status_code == 409
    assert next_step(api) == question
    stored = store.get("demo")
    assert stored is not None and stored.state.attempts == ()


def test_answering_the_same_question_twice_is_refused() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    question = next_step(api)
    key = question["options"][0]["key"]
    assert answer(api, question["pack_id"], key).status_code == 200

    assert answer(api, question["pack_id"], key).status_code == 409


def test_a_stale_answer_after_the_last_question_never_ends_the_match() -> None:
    store = MemoryLearnerStore()
    api = client(store)
    started(api)
    last: dict[str, Any] = {}
    while (step := next_step(api))["kind"] == "question":
        last = step
        answer(api, step["pack_id"], step["options"][0]["key"])
        # The match's last answer: the next request would reach full time.
        repeat = answer(api, step["pack_id"], step["options"][0]["key"])
        assert repeat.status_code == 409
        assert api.get("/api/viewers/demo").json()["match_number"] == 1
    assert last and step["match_number"] == 1


def test_an_option_the_question_does_not_have_is_refused() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    question = next_step(api)

    assert answer(api, question["pack_id"], "Z").status_code == 422


def test_viewer_ids_must_be_plain() -> None:
    api = client(MemoryLearnerStore())

    assert api.post("/api/viewers", json={"viewer_id": "../escape"}).status_code == 422
    assert api.post("/api/viewers", json={"viewer_id": "Lily"}).status_code == 422
    assert api.get("/api/viewers/Lily").status_code == 422
    assert api.post("/api/viewers/a%2F..%2Fb/next").status_code in {404, 422}


def test_an_unknown_viewer_must_start_first() -> None:
    api = client(MemoryLearnerStore())

    assert api.get("/api/viewers/nobody").status_code == 404
    assert api.post("/api/viewers/nobody/next").status_code == 404


def test_starting_again_carries_on_and_a_name_chooses_its_matches() -> None:
    api = client(MemoryLearnerStore())
    first = api.post("/api/viewers", json={"viewer_id": "lily"}).json()

    again = api.post("/api/viewers", json={"viewer_id": "lily", "seed": 1}).json()

    assert first == again
    assert first["match_number"] == 1 and first["matches"] == MATCHES_PER_SESSION
    assert first["fixture"]["home"] and first["fixture"]["away"]
    assert [bar["name"] for bar in first["concepts"]] == list(course().names().values())


def test_a_viewer_who_has_watched_every_match_is_told_so() -> None:
    store = MemoryLearnerStore()
    store.create(LearnerState("done", SEED, match_number=MATCHES_PER_SESSION + 1))
    api = client(store)

    status = api.get("/api/viewers/done").json()

    assert status["finished"] is True and status["fixture"] is None
    assert api.post("/api/viewers/done/next").status_code == 409
    assert answer(api, "0" * 16, "A", viewer_id="done").status_code == 409


def test_a_reloaded_page_carries_on_at_the_same_question(tmp_path: Path) -> None:
    first_page = client(JsonLearnerStore(tmp_path))
    started(first_page)
    question = next_step(first_page)
    answer(first_page, question["pack_id"], question["options"][0]["key"])
    waiting = next_step(first_page)

    reloaded = client(JsonLearnerStore(tmp_path))

    assert started(reloaded)["match_number"] == 1
    assert next_step(reloaded) == waiting


def test_the_built_page_is_served_outside_the_api(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<p>page</p>")
    (tmp_path / "assets" / "app.js").write_text("run()")
    (tmp_path.parent / "secret.txt").write_text("no")
    api = client(MemoryLearnerStore(), frontend=tmp_path)

    assert api.get("/").text == "<p>page</p>"
    assert api.get("/assets/app.js").text == "run()"
    assert api.get("/match/2").text == "<p>page</p>"
    assert api.get("/..%2Fsecret.txt").text == "<p>page</p>"
    assert api.get("/api/nothing").status_code == 404


def test_each_question_carries_the_score_and_a_catch_up_after_the_first() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    first = next_step(api)
    answer(api, first["pack_id"], first["options"][0]["key"])

    second = next_step(api)

    assert first["catch_up"] is None
    assert first["score"]["clock"] == first["delivered"]["clock"]
    if second["kind"] == "question":
        assert second["catch_up"].endswith(
            f"{second['score']['home']}\N{EN DASH}{second['score']['away']}."
        )
