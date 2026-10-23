"""The same words for the same question: a Tutor that remembers what it said.

The web server keeps no session, so each request replays the viewer's match up to the waiting
question, and asks the Tutor for its words again. `CachedTutor` answers those replays with the
words the viewer already saw: a question by its pack, and feedback by its pack, the option
picked and the viewer's recent answers. It never calls a model twice for the same thing.

Nothing about the viewer is in a prompt, so two viewers who meet the same pack can share its
words. The cache is bounded, and forgets the least recently used entries first.

The server answers several viewers at once, so the cache is safe to share between threads. It
never holds its lock while the model words something, so one slow wording doesn't hold up
another viewer. If two viewers ask for the same words at once, both are worded, and both get
whichever was kept first, so nobody sees words that are later replaced.
"""

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from typing import TypeVar

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.tutor.base import NO_HISTORY, History, Tutor, TutorFeedback, TutorQuestion

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
    _feedback: OrderedDict[tuple[str, str | None, History], TutorFeedback] = field(
        default_factory=OrderedDict[tuple[str, str | None, History], TutorFeedback],
        init=False,
        repr=False,
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def question(self, view: QuestionView) -> TutorQuestion:
        """The words this question was first given."""
        return _remembered(
            self._questions,
            view.pack_id,
            lambda: self.inner.question(view),
            self.size,
            self._lock,
        )

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        """The feedback this pick of this question was first given, after the same history.

        The history is part of the key: words that mention one viewer's recent answers must
        never reach a viewer whose answers were different.
        """
        return _remembered(
            self._feedback,
            (pack.pack_id, grade.chosen, history),
            lambda: self.inner.feedback(pack, grade, history),
            self.size,
            self._lock,
        )

    def remembers_question(self, view: QuestionView) -> bool:
        """Whether this question's words are already kept, so wording it again costs nothing."""
        with self._lock:
            return view.pack_id in self._questions

    def remembers_feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> bool:
        """Whether this pick's feedback, after this history, is already kept."""
        with self._lock:
            return (pack.pack_id, grade.chosen, history) in self._feedback


def _remembered(
    cache: OrderedDict[KeyT, ValueT],
    key: KeyT,
    make: Callable[[], ValueT],
    size: int,
    lock: threading.Lock,
) -> ValueT:
    with lock:
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
    value = make()
    with lock:
        kept = cache.setdefault(key, value)
        cache.move_to_end(key)
        while len(cache) > size:
            cache.popitem(last=False)
        return kept
