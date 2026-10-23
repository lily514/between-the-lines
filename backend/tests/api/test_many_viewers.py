"""Serving many viewers at once: one viewer's requests take turns, and nobody else waits."""

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from btl.api import app as api_app
from btl.api.app import create_app
from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.learn.session import Course, PreparedMatch
from btl.schema.ids import TeamId
from btl.store.memory import MemoryLearnerStore
from btl.tutor.base import NO_HISTORY, History, TutorFeedback, TutorQuestion
from btl.tutor.templates import TemplateTutor
from tests.api.test_app import NOW, SEED
from tests.fixtures.learning import threat_model

# Long enough never to trip on a slow machine; a passing test never waits for it.
PATIENCE = 10.0


class Stalling:
    """The template Tutor, except that the first question waits until the test lets it go.

    It stands in for a model call that takes a while, so a test can see who else has to wait.
    """

    def __init__(self) -> None:
        self.template = TemplateTutor()
        self.stalled = threading.Event()
        self.go_on = threading.Event()
        self._first = True
        self._guard = threading.Lock()

    def question(self, view: QuestionView) -> TutorQuestion:
        with self._guard:
            first, self._first = self._first, False
        if first:
            self.stalled.set()
            assert self.go_on.wait(PATIENCE)
        return self.template.question(view)

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        return self.template.feedback(pack, grade, history)


class Request(threading.Thread):
    """One request on its own thread, keeping the response for the test to read."""

    def __init__(self, send: Callable[[], Any]) -> None:
        super().__init__(daemon=True)
        self._send = send
        self.response: Any = None

    def run(self) -> None:
        self.response = self._send()


def server(tutor: Stalling) -> TestClient:
    course = Course(threat_model(), tutor)
    api = TestClient(create_app(lambda: course, MemoryLearnerStore(), lambda: NOW))
    for viewer_id in ("ana", "ben"):
        started = api.post("/api/viewers", json={"viewer_id": viewer_id, "seed": SEED})
        assert started.status_code == 200, started.text
    return api


def test_a_slow_question_for_one_viewer_doesnt_hold_up_another() -> None:
    tutor = Stalling()
    api = server(tutor)
    ana = Request(lambda: api.post("/api/viewers/ana/next"))
    ana.start()
    assert tutor.stalled.wait(PATIENCE)

    ben = Request(lambda: api.post("/api/viewers/ben/next"))
    ben.start()
    ben.join(PATIENCE)

    assert not ben.is_alive() and ben.response.status_code == 200
    assert ana.is_alive()  # still waiting for its words
    tutor.go_on.set()
    ana.join(PATIENCE)
    assert ana.response.status_code == 200


def test_one_viewer_s_requests_take_turns() -> None:
    tutor = Stalling()
    api = server(tutor)
    first = Request(lambda: api.post("/api/viewers/ana/next"))
    first.start()
    assert tutor.stalled.wait(PATIENCE)

    reload = Request(lambda: api.post("/api/viewers/ana/next"))
    reload.start()
    reload.join(0.3)

    assert reload.is_alive()  # waiting for the first request to finish
    tutor.go_on.set()
    first.join(PATIENCE)
    reload.join(PATIENCE)
    assert first.response.status_code == reload.response.status_code == 200
    assert first.response.json() == reload.response.json()


def test_the_health_check_answers_without_loading_anything(tmp_path: Path) -> None:
    def refuse() -> Course:
        raise AssertionError("the health check must not load the course")

    (tmp_path / "index.html").write_text("<p>page</p>")
    api = TestClient(create_app(refuse, MemoryLearnerStore(), lambda: NOW, tmp_path))

    response = api.get("/api/health")

    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_the_least_recently_used_prepared_match_is_dropped_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared: list[int] = []
    real = api_app.prepare_match

    def counted(course: Course, seed: int, match_number: int, club: TeamId | None) -> PreparedMatch:
        prepared.append(seed)
        return real(course, seed, match_number, club)

    monkeypatch.setattr(api_app, "prepare_match", counted)
    course = Course(threat_model(), TemplateTutor())
    api = TestClient(create_app(lambda: course, MemoryLearnerStore(), lambda: NOW, prepared_size=1))
    api.post("/api/viewers", json={"viewer_id": "ana", "seed": 7})
    api.post("/api/viewers", json={"viewer_id": "ben", "seed": 8})

    for viewer_id in ("ana", "ana", "ben", "ana"):
        assert api.post(f"/api/viewers/{viewer_id}/next").status_code == 200

    assert prepared == [7, 8, 7]  # ana's match was kept, then dropped for ben's
