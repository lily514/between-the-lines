"""Limits on the model's work for a public demo: so many wordings per viewer a day, and in all.

Only the model's wordings cost money; the template's are free. So past a limit the template words
it, as it does after any model failure, and the demo carries on. A wording is one question or one
feedback, and costs at most two model calls (the first try and one repair), so a limit on
wordings bounds the calls at twice as many. Words the cache already holds cost nothing and aren't
counted.

The counts are kept in memory by UTC day, and a restart starts them again; the model
deployment's own token cap still holds. The server runs a single replica, so its count is the
whole count.
"""

import threading
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from datetime import date

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.tutor.base import NO_HISTORY, History, Tutor, TutorFeedback, TutorQuestion
from btl.tutor.cached import CachedTutor

# At most 120 model calls per viewer a day (about one and a half sessions of three matches), and
# 2,000 in all (about $0.50 a day).
WORDINGS_PER_VIEWER = 60
WORDINGS_PER_DAY = 1000
LIMITED = "template (daily limit)"

# Whose request is being served. The API sets it for each viewer's request; the Tutor protocol
# never sees the viewer, so this is how the limit knows whose wording it is counting.
current_viewer: ContextVar[str | None] = ContextVar("current_viewer", default=None)


@dataclass
class Allowance:
    """How many wordings are left today, for each viewer and in all.

    ``today`` gives the current UTC date; it is a parameter so tests can move the day on.
    """

    per_viewer: int
    per_day: int
    today: Callable[[], date]
    _day: date | None = field(default=None, init=False, repr=False)
    _used: dict[str, int] = field(default_factory=dict[str, int], init=False, repr=False)
    _total: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def take(self, viewer: str) -> bool:
        """Count one wording for ``viewer`` if both limits allow it; False if either is spent."""
        with self._lock:
            day = self.today()
            if day != self._day:
                self._day, self._used, self._total = day, {}, 0
            used = self._used.get(viewer, 0)
            if used >= self.per_viewer or self._total >= self.per_day:
                return False
            self._used[viewer] = used + 1
            self._total += 1
            return True


@dataclass
class LimitedTutor:
    """A `btl.tutor.base.Tutor`: the model's words while the allowance lasts, then the fallback's.

    Words already in the cache are served whatever the allowance, since they cost nothing; so a
    reload shows the same words even after a limit is reached.
    """

    inner: CachedTutor
    fallback: Tutor
    allowance: Allowance

    def question(self, view: QuestionView) -> TutorQuestion:
        """The model's question if it is cached or the allowance lasts, else the fallback's."""
        if self.inner.remembers_question(view) or self._allowed():
            return self.inner.question(view)
        return self.fallback.question(view)

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        """The model's feedback if it is cached or the allowance lasts, else the fallback's."""
        if self.inner.remembers_feedback(pack, grade, history) or self._allowed():
            return self.inner.feedback(pack, grade, history)
        return replace(self.fallback.feedback(pack, grade, history), source=LIMITED)

    def _allowed(self) -> bool:
        return self.allowance.take(current_viewer.get() or "")
