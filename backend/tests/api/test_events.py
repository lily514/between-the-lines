"""The events the demo reports: one JSON line for each step of the loop, for Log Analytics."""

import json
import logging
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from btl.api.app import create_app
from btl.api.events import LOGGER
from btl.api.limits import Allowance, LimitedTutor
from btl.learn.session import Course
from btl.store.memory import MemoryLearnerStore
from btl.tutor.cached import CachedTutor
from btl.tutor.templates import TemplateTutor
from tests.api.test_app import NOW, SEED, course
from tests.fixtures.learning import threat_model
from tests.tutor.test_cached import Counting


def events(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    return [json.loads(record.getMessage()) for record in caplog.records if record.name == LOGGER]


def test_a_match_reports_each_question_answer_and_mastery_move_then_full_time(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER)
    api = TestClient(create_app(course, MemoryLearnerStore(), lambda: NOW))
    api.post("/api/viewers", json={"viewer_id": "ana", "seed": SEED})
    answered = 0
    while (step := api.post("/api/viewers/ana/next").json())["kind"] == "question":
        key = step["options"][0]["key"]
        api.post("/api/viewers/ana/answers", json={"pack_id": step["pack_id"], "key": key})
        answered += 1

    reported = events(caplog)
    kinds = [event["event"] for event in reported]
    asked = next(event for event in reported if event["event"] == "question_asked")
    graded = next(event for event in reported if event["event"] == "answer_graded")
    moved = next(event for event in reported if event["event"] == "mastery_updated")

    assert kinds.count("question_asked") == kinds.count("answer_graded") == answered > 0
    assert kinds.count("mastery_updated") == answered and kinds[-1] == "full_time"
    assert set(asked) == {
        "event",
        "viewer_id",
        "match_number",
        "pack_id",
        "concept",
        "level",
        "form",
        "delivery",
    }
    assert graded["viewer_id"] == "ana" and graded["source"] == "template"
    assert graded["concept"] == moved["concept"] and 0 <= moved["after"] <= 1
    assert reported[-1] == {
        "event": "full_time",
        "viewer_id": "ana",
        "match_number": 1,
        "finished": False,
    }


def test_a_spent_limit_is_reported_with_whose_it_was(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER)
    allowance = Allowance(per_viewer=0, per_day=10, today=lambda: date(2026, 10, 23))
    limited = LimitedTutor(CachedTutor(Counting()), TemplateTutor(), allowance)
    limited_course = Course(threat_model(), limited)
    api = TestClient(create_app(lambda: limited_course, MemoryLearnerStore(), lambda: NOW))
    api.post("/api/viewers", json={"viewer_id": "ana", "seed": SEED})

    api.post("/api/viewers/ana/next")

    assert {
        "event": "limit_reached",
        "viewer_id": "ana",
        "kind": "question",
        "scope": "viewer",
    } in (events(caplog))
