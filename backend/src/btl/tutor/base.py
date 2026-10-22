"""What a Tutor is: two calls, one before the viewer answers and one after."""

from dataclasses import dataclass
from typing import Protocol

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade


@dataclass(frozen=True, slots=True)
class TutorQuestion:
    """The question's wording, with ``{slots}`` for facts."""

    text: str


@dataclass(frozen=True, slots=True)
class TutorFeedback:
    """The feedback's wording after the code-written verdict, with ``{slots}`` for facts.

    ``source`` says who wrote it, for logs and the screen: "template" here, a model's name in
    Milestone 2b. ``misconception`` is a common mix-up, offered after a wrong answer; it is kept
    apart from the explanation so a page can set it aside.
    """

    explanation: str
    takeaway: str
    source: str
    misconception: str | None = None


@dataclass(frozen=True, slots=True)
class History:
    """The viewer's recent answers on the concept, before this one: no id, no name, no club.

    ``recent`` is right (True) or wrong (False), oldest first. ``last_wrong`` is what the
    question asked when they last got it wrong ("where to pass"), if they ever did.
    """

    recent: tuple[bool, ...] = ()
    last_wrong: str | None = None


NO_HISTORY = History()


class Tutor(Protocol):
    """Writes a question's wording and its feedback."""

    def question(self, view: QuestionView) -> TutorQuestion:
        """Word the question from what the viewer may know before answering."""
        ...

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        """Explain the answer from the whole pack, and perhaps the viewer's recent answers."""
        ...
