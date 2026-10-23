import threading
from dataclasses import dataclass, field

from btl.learn.evidence import EvidencePack, QuestionView, question_view
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.base import NO_HISTORY, History, TutorFeedback, TutorQuestion
from btl.tutor.cached import CachedTutor
from tests.fixtures.packs import every_kind, first_of

PACK = first_of(Asks.WHERE_TO_PASS)


@dataclass
class Counting:
    """A Tutor that numbers its words, so a test can tell a fresh call from a remembered one."""

    calls: list[str] = field(default_factory=list[str])

    def question(self, view: QuestionView) -> TutorQuestion:
        self.calls.append(f"question {view.pack_id}")
        return TutorQuestion(f"question {len(self.calls)}")

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        self.calls.append(f"feedback {pack.pack_id} {grade.chosen} {history.recent}")
        return TutorFeedback(f"feedback {len(self.calls)}", "x", "counting")


def test_the_same_question_is_worded_once() -> None:
    inner = Counting()
    cached = CachedTutor(inner)

    first, again = cached.question(question_view(PACK)), cached.question(question_view(PACK))

    assert first == again and len(inner.calls) == 1


def test_each_pick_gets_its_own_feedback_and_keeps_it() -> None:
    inner = Counting()
    cached = CachedTutor(inner)
    a, b = (Grade(correct=o.correct, chosen=o.key) for o in PACK.options[:2])

    first = cached.feedback(PACK, a)
    other = cached.feedback(PACK, b)
    again = cached.feedback(PACK, a)

    assert first == again != other and len(inner.calls) == 2


def test_the_least_recently_used_words_are_forgotten_first() -> None:
    inner = Counting()
    cached = CachedTutor(inner, size=2)
    one, two, three = (question_view(pack) for pack in every_kind(0)[:3])

    cached.question(one)
    cached.question(two)
    cached.question(one)  # one is now the most recent
    cached.question(three)  # so two is forgotten
    cached.question(one)
    cached.question(two)

    assert inner.calls == [f"question {v.pack_id}" for v in (one, two, three, two)]


def test_feedback_after_a_different_history_is_worded_again() -> None:
    inner = Counting()
    cached = CachedTutor(inner)
    pick = Grade(correct=True, chosen=PACK.correct_key)

    plain = cached.feedback(PACK, pick)
    after_two_right = cached.feedback(PACK, pick, History((True, True)))
    again = cached.feedback(PACK, pick, History((True, True)))

    assert plain != after_two_right == again and len(inner.calls) == 2


@dataclass
class Gated(Counting):
    """A `Counting` Tutor whose first wording waits until the test lets it go."""

    stalled: threading.Event = field(default_factory=threading.Event)
    go_on: threading.Event = field(default_factory=threading.Event)

    def question(self, view: QuestionView) -> TutorQuestion:
        worded = super().question(view)
        if len(self.calls) == 1:
            self.stalled.set()
            assert self.go_on.wait(10)
        return worded


def test_viewers_asking_for_the_same_words_at_once_all_get_the_words_kept() -> None:
    inner = Gated()
    cached = CachedTutor(inner)
    view = question_view(PACK)
    slow: list[TutorQuestion] = []
    first = threading.Thread(target=lambda: slow.append(cached.question(view)))
    first.start()
    assert inner.stalled.wait(10)

    meanwhile = cached.question(view)  # not held up by the first wording
    inner.go_on.set()
    first.join(10)

    assert meanwhile == TutorQuestion("question 2")
    assert slow == [meanwhile] and cached.question(view) == meanwhile
