"""The model's daily limits: past them the template words it, and cached words are always free."""

from datetime import date

from fastapi.testclient import TestClient

from btl.api.app import create_app
from btl.api.limits import LIMITED, Allowance, LimitedTutor, current_viewer
from btl.learn.evidence import question_view
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.learn.session import Course
from btl.store.memory import MemoryLearnerStore
from btl.tutor.cached import CachedTutor
from btl.tutor.foundry import FoundryTutor
from btl.tutor.templates import TemplateTutor
from btl.tutor.verified import VerifiedTutor
from tests.api.test_app import NOW, SEED
from tests.fixtures.learning import threat_model
from tests.fixtures.packs import every_kind, first_of
from tests.fixtures.tutor import QUESTION, ByKind
from tests.tutor.test_cached import Counting

PACK = first_of(Asks.WHERE_TO_PASS)
DAY = date(2026, 10, 23)


def test_each_viewer_has_their_own_allowance_within_the_day_s() -> None:
    allowance = Allowance(per_viewer=2, per_day=3, today=lambda: DAY)

    taken = [allowance.take(viewer) for viewer in ("ana", "ana", "ana", "ben", "cat")]

    # ana's two, then ana's limit; ben has the day's third, so cat meets the day's limit.
    assert taken == [None, None, "viewer", None, "day"]


def test_a_new_day_starts_every_allowance_again() -> None:
    today = [DAY]
    allowance = Allowance(per_viewer=1, per_day=1, today=lambda: today[0])
    assert allowance.take("ana") is None and allowance.take("ana") == "viewer"

    today[0] = date(2026, 10, 24)

    assert allowance.take("ana") is None


def test_past_the_limit_the_template_words_it_and_says_why() -> None:
    inner = Counting()
    tutor = LimitedTutor(
        CachedTutor(inner), TemplateTutor(), Allowance(per_viewer=1, per_day=10, today=lambda: DAY)
    )
    template = TemplateTutor()
    pick = Grade(correct=True, chosen=PACK.correct_key)
    token = current_viewer.set("ana")
    try:
        question = tutor.question(question_view(PACK))
        feedback = tutor.feedback(PACK, pick)
    finally:
        current_viewer.reset(token)

    assert question.text == "question 1"  # the model's: the allowance had one wording
    assert feedback.explanation == template.feedback(PACK, pick).explanation
    assert feedback.source == LIMITED
    assert len(inner.calls) == 1


def test_words_already_cached_are_free_even_past_the_limit() -> None:
    inner = Counting()
    tutor = LimitedTutor(
        CachedTutor(inner), TemplateTutor(), Allowance(per_viewer=1, per_day=10, today=lambda: DAY)
    )
    first, other = (question_view(pack) for pack in every_kind(0)[:2])
    token = current_viewer.set("ana")
    try:
        worded = tutor.question(first)
        tutor.question(other)  # the limit is reached here: the template words it
        again = tutor.question(first)
    finally:
        current_viewer.reset(token)

    assert again == worded and len(inner.calls) == 1


def test_through_the_api_one_viewer_s_limit_leaves_another_s_alone() -> None:
    model = ByKind(fail_every=1000)
    verified = VerifiedTutor(FoundryTutor(model), TemplateTutor())
    allowance = Allowance(per_viewer=1, per_day=10, today=lambda: DAY)
    course = Course(threat_model(), LimitedTutor(CachedTutor(verified), TemplateTutor(), allowance))
    api = TestClient(create_app(lambda: course, MemoryLearnerStore(), lambda: NOW))
    for viewer in ("ana", "ben"):
        api.post("/api/viewers", json={"viewer_id": viewer, "seed": SEED})

    question = api.post("/api/viewers/ana/next").json()
    reload = api.post("/api/viewers/ana/next").json()
    key = question["options"][0]["key"]
    feedback = api.post(
        "/api/viewers/ana/answers", json={"pack_id": question["pack_id"], "key": key}
    ).json()
    bens = api.post("/api/viewers/ben/next").json()
    bens_feedback = api.post(
        "/api/viewers/ben/answers", json={"pack_id": bens["pack_id"], "key": key}
    ).json()

    assert question["text"].startswith(QUESTION.split("{")[0])  # ana's one wording: the model's
    assert reload == question  # the same words, from the cache
    assert feedback["source"] == LIMITED  # ana's allowance is spent
    assert bens["text"] == question["text"]  # the same question's cached words cost ben nothing
    assert bens_feedback["source"] == model.model  # so ben's allowance pays for his feedback
