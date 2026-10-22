"""The web page with the model's words: each question worded once, nothing learned differently."""

from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from btl.api.app import create_app
from btl.learn.learner import MATCHES_PER_SESSION, Attempt
from btl.learn.session import Course, DemoViewer, choose_club, start_session, watch_match
from btl.schema.ids import TeamId
from btl.store.memory import MemoryLearnerStore
from btl.tutor.base import Tutor
from btl.tutor.cached import CachedTutor
from btl.tutor.foundry import FoundryTutor
from btl.tutor.templates import TemplateTutor
from btl.tutor.verified import VerifiedTutor
from tests.api.test_app import NOW, SEED
from tests.fixtures.learning import threat_model
from tests.fixtures.tutor import ByKind

HEXHAM = 2


def model_tutor(fake: ByKind, cached: bool = True) -> Tutor:
    verified = VerifiedTutor(FoundryTutor(fake), TemplateTutor())
    return CachedTutor(verified) if cached else verified


def terminal_attempts(club: int | None) -> tuple[Attempt, ...]:
    """What the scripted demo viewer answers in the terminal over three matches, with templates."""
    course = Course(threat_model(), TemplateTutor())
    store = MemoryLearnerStore()
    start_session(store, "demo", SEED)
    if club is not None:
        choose_club(course, store, "demo", TeamId(club))
    viewer = DemoViewer()
    for _ in range(MATCHES_PER_SESSION):
        watch_match(course, store, "demo", viewer, lambda: NOW)
    stored = store.get("demo")
    assert stored is not None
    return stored.state.attempts


def play(api: TestClient, expected: list[Attempt], club: int | None) -> list[dict[str, Any]]:
    """Answer as the terminal's demo viewer did; returns every question payload, in order."""
    body: dict[str, object] = {"viewer_id": "demo", "seed": SEED}
    if club is not None:
        body["club"] = club
    assert api.post("/api/viewers", json=body).status_code == 200
    questions: list[dict[str, Any]] = []
    finished = 0
    while finished < MATCHES_PER_SESSION:
        step = api.post("/api/viewers/demo/next").json()
        if step["kind"] == "full_time":
            finished += 1
            continue
        assert api.post("/api/viewers/demo/next").json() == step  # A reload shows the same words.
        questions.append(step)
        attempt = expected.pop(0)
        assert step["pack_id"] == attempt.pack_id
        answered = api.post(
            "/api/viewers/demo/answers", json={"pack_id": step["pack_id"], "key": attempt.chosen}
        )
        assert answered.status_code == 200, answered.text
        assert answered.json()["source"].split(" (")[0] in {"fake-model", "template"}
    return questions


@pytest.mark.parametrize("club", [None, HEXHAM], ids=["no club", "supporting a club"])
def test_the_page_with_the_model_gives_the_terminal_s_record_and_words_each_thing_once(
    club: int | None,
) -> None:
    fake = ByKind()
    store = MemoryLearnerStore()
    api = TestClient(
        create_app(lambda: Course(threat_model(), model_tutor(fake)), store, lambda: NOW)
    )
    expected = terminal_attempts(club)

    questions = play(api, list(expected), club)

    stored = store.get("demo")
    assert stored is not None
    assert [replace(a, answered_at="") for a in stored.state.attempts] == [
        replace(a, answered_at="") for a in expected
    ]
    asked = [r for r in fake.requests if r.schema_name == "question"]
    first_feedback = [
        r
        for r in fake.requests
        if r.schema_name == "feedback" and "Your last reply" not in r.prompt
    ]
    assert len(asked) == len(questions) == len(first_feedback)
    for question in questions:
        assert "{" not in question["text"]
        assert not {"correct", "correct_key", "outcome", "explanation"} & set(question)


def test_without_the_cache_a_question_would_be_worded_on_every_replay() -> None:
    fake = ByKind()
    api = TestClient(
        create_app(
            lambda: Course(threat_model(), model_tutor(fake, cached=False)),
            MemoryLearnerStore(),
            lambda: NOW,
        )
    )
    api.post("/api/viewers", json={"viewer_id": "demo", "seed": SEED})

    step = api.post("/api/viewers/demo/next").json()
    api.post("/api/viewers/demo/next")
    api.post("/api/viewers/demo/answers", json={"pack_id": step["pack_id"], "key": "A"})

    assert len([r for r in fake.requests if r.schema_name == "question"]) == 3
