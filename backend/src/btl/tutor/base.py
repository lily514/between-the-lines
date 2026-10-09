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
    Milestone 2b.
    """

    explanation: str
    takeaway: str
    source: str


class Tutor(Protocol):
    """Writes a question's wording and its feedback."""

    def question(self, view: QuestionView) -> TutorQuestion:
        """Word the question from what the viewer may know before answering."""
        ...

    def feedback(self, pack: EvidencePack, grade: Grade) -> TutorFeedback:
        """Explain the answer from the whole pack."""
        ...
