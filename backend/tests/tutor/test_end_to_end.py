"""The model's words never change what is learned, and every word shown has been checked."""

import pytest

from btl.learn.learner import MATCHES_PER_SESSION, Attempt
from btl.learn.session import Course, DemoViewer, choose_club, start_session, watch_match
from btl.schema.ids import TeamId
from btl.store.memory import MemoryLearnerStore
from btl.tutor.base import Tutor
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
