"""The model's words never change what is learned, and every word shown has been checked."""

from dataclasses import dataclass, field

import pytest

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.learn.learner import MATCHES_PER_SESSION, Attempt
from btl.learn.session import (
    RECENT_ANSWERS,
    Course,
    DemoViewer,
    choose_club,
    start_session,
    watch_match,
)
from btl.schema.ids import TeamId
from btl.store.memory import MemoryLearnerStore
from btl.tutor.base import NO_HISTORY, History, Tutor, TutorFeedback, TutorQuestion
from btl.tutor.foundry import FoundryTutor
from btl.tutor.templates import TemplateTutor
from btl.tutor.verified import CheckRecord, VerifiedTutor
from tests.fixtures.learning import threat_model
from tests.fixtures.tutor import QUESTION, ByKind

NOW = "2026-10-22T12:00:00+00:00"
HEXHAM = TeamId(2)


def watch_three(tutor: Tutor, club: TeamId | None) -> tuple[tuple[Attempt, ...], DemoViewer]:
    course = Course(threat_model(), tutor)
    store = MemoryLearnerStore()
    start_session(store, "demo", seed=7)
    if club is not None:
        choose_club(course, store, "demo", club)
    viewer = DemoViewer()
    for _ in range(MATCHES_PER_SESSION):
        watch_match(course, store, "demo", viewer, lambda: NOW)
    stored = store.get("demo")
    assert stored is not None
    return stored.state.attempts, viewer


@pytest.mark.parametrize("club", [None, HEXHAM], ids=["no club", "supporting a club"])
def test_the_model_s_words_never_change_what_is_learned(club: TeamId | None) -> None:
    records: list[CheckRecord] = []
    model = VerifiedTutor(FoundryTutor(ByKind()), TemplateTutor(), records.append)

    with_template, _ = watch_three(TemplateTutor(), club)
    with_model, viewer = watch_three(model, club)

    assert with_model == with_template
    sources = {told.source.split(" (")[0] for told in viewer.seen}
    assert sources == {"fake-model", "template"}
    assert all(record.passed for record in records if record.kind == "question")
    team_names = {told.pack.context["team"].display for told in viewer.seen}
    for told in viewer.seen:
        assert "{" not in told.explanation + told.takeaway
        if told.source == "fake-model":
            assert (
                told.takeaway.removeprefix("Watch how ").removesuffix(" played it.") in team_names
            )
    assert all(asked.text != QUESTION and "{" not in asked.text for asked in viewer.asked)


@dataclass
class Listening:
    """The template Tutor, noting the history each feedback is given."""

    heard: list[tuple[str, History]] = field(default_factory=list[tuple[str, History]])

    def question(self, view: QuestionView) -> TutorQuestion:
        return TemplateTutor().question(view)

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        self.heard.append((pack.concept.key, history))
        return TemplateTutor().feedback(pack, grade, history)


def test_each_feedback_hears_the_viewer_s_earlier_answers_on_its_concept() -> None:
    tutor = Listening()

    attempts, _ = watch_three(tutor, None)

    assert len(tutor.heard) == len(attempts)
    for index, (concept, history) in enumerate(tutor.heard):
        earlier = [a.correct for a in attempts[:index] if a.concept == concept]
        assert history.recent == tuple(earlier[-RECENT_ANSWERS:])
        wrong = [a.asks.value for a in attempts[:index] if a.concept == concept and not a.correct]
        assert history.last_wrong == (wrong[-1] if wrong else None)
