"""The same words for the same question: a Tutor that remembers what it said.

The web server keeps no session, so each request replays the viewer's match up to the waiting
question, and asks the Tutor for its words again. `CachedTutor` answers those replays with the
words the viewer already saw: a question by its pack, and feedback by its pack and the option
picked. It never calls a model twice for the same thing.

Nothing about the viewer is in a prompt, so two viewers who meet the same pack can share its
words. The cache is bounded, and forgets the least recently used entries first.
"""

from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from typing import TypeVar

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.tutor.base import Tutor, TutorFeedback, TutorQuestion

# Questions and feedback kept, each.
CACHE_SIZE = 2048

KeyT = TypeVar("KeyT", bound=Hashable)
ValueT = TypeVar("ValueT")


@dataclass
class CachedTutor:
    """A `btl.tutor.base.Tutor` that words each question, and each pick's feedback, once."""

    inner: Tutor
    size: int = CACHE_SIZE
    _questions: OrderedDict[str, TutorQuestion] = field(
        default_factory=OrderedDict[str, TutorQuestion], init=False, repr=False
    )
    _feedback: OrderedDict[tuple[str, str | None], TutorFeedback] = field(
        default_factory=OrderedDict[tuple[str, str | None], TutorFeedback], init=False, repr=False
    )

    def question(self, view: QuestionView) -> TutorQuestion:
        """The words this question was first given."""
        return _remembered(
            self._questions, view.pack_id, lambda: self.inner.question(view), self.size
        )

    def feedback(self, pack: EvidencePack, grade: Grade) -> TutorFeedback:
        """The feedback this pick of this question was first given."""
        return _remembered(
            self._feedback,
            (pack.pack_id, grade.chosen),
            lambda: self.inner.feedback(pack, grade),
            self.size,
        )


def _remembered(
    cache: OrderedDict[KeyT, ValueT], key: KeyT, make: Callable[[], ValueT], size: int
) -> ValueT:
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    value = make()
    cache[key] = value
    while len(cache) > size:
        cache.popitem(last=False)
    return value
