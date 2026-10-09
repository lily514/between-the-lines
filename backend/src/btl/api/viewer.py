"""The web page as a session viewer, which stops the session where a request ends.

`watch_match` asks its viewer each question and waits for the answer. Over HTTP the answer
arrives in a later request, so `WebViewer` stops the session instead, by raising: in ``ask``
when it has no answer for the question (the request returns that question), and in ``tell``
once the feedback is in (the answer was saved just before). The next request replays the match
from the saved answers and arrives at exactly the same place.
"""

from dataclasses import dataclass, field

from btl.learn.grader import Answer, ChoiceAnswer
from btl.learn.learner import LearnerState
from btl.learn.session import Asked, MatchStart, Told
from btl.store.base import LearnerStore, Stored


class QuestionPendingError(Exception):
    """The session reached a question nobody has answered yet."""

    def __init__(self, asked: Asked) -> None:
        """Hold the question."""
        super().__init__(asked.pack.pack_id)
        self.asked = asked


class FeedbackGivenError(Exception):
    """The answer was graded and saved, and this is what the viewer is told."""

    def __init__(self, told: Told) -> None:
        """Hold the feedback."""
        super().__init__(told.pack.pack_id)
        self.told = told


class NotPendingError(Exception):
    """An answer named a question that isn't the one waiting to be answered."""


class BadKeyError(Exception):
    """An answer named an option the question doesn't have."""


@dataclass
class WebViewer:
    """A `btl.learn.session.Viewer` that answers at most one question, then stops the session.

    With no answer, it stops at the first question it is asked. With one, that question must be
    ``answer``'s ``pack_id``; it answers it and stops once the feedback is given.
    """

    answer: tuple[str, str] | None = None
    start: MatchStart | None = None
    ended: tuple[dict[str, float], int] | None = None
    _answered: bool = field(default=False, init=False)

    def begin(self, start: MatchStart) -> None:
        """Note the match, for the full-time summary."""
        self.start = start

    def ask(self, asked: Asked) -> Answer:
        """Give the request's answer, or stop at this question.

        Raises:
            QuestionPendingError: If there is no answer for it.
            NotPendingError: If the answer was meant for another question.
            BadKeyError: If the answer's key isn't one of the options.
        """
        if self.answer is None or self._answered:
            raise QuestionPendingError(asked)
        pack_id, key = self.answer
        if pack_id != asked.pack.pack_id:
            raise NotPendingError(pack_id)
        if key not in {option.key for option in asked.pack.options}:
            raise BadKeyError(key)
        self._answered = True
        return ChoiceAnswer(key)

    def tell(self, told: Told) -> None:
        """Stop the session with the feedback.

        Raises:
            FeedbackGivenError: Always.
        """
        raise FeedbackGivenError(told)

    def end(self, mastery: dict[str, float], asked: int) -> None:
        """Note the bars and the number of questions at full time."""
        self.ended = (mastery, asked)


@dataclass
class AnswerOnlyStore:
    """A store that saves answers but refuses to move on to the next match.

    An answer request must never finish a match: if no question is waiting, the session would
    otherwise run to full time and save that, as a side effect of a stale answer.
    """

    store: LearnerStore
    match_number: int

    def get(self, viewer_id: str) -> Stored | None:
        """Read through to the real store."""
        return self.store.get(viewer_id)

    def create(self, state: LearnerState) -> str:
        """Create through the real store."""
        return self.store.create(state)

    def put(self, state: LearnerState, etag: str) -> str:
        """Save an answer in the same match.

        Raises:
            NotPendingError: If the save would start the next match.
        """
        if state.match_number != self.match_number:
            raise NotPendingError("no question is waiting to be answered")
        return self.store.put(state, etag)
