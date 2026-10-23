"""The Tutor the viewer meets: the model's words if they pass the Verifier, else the template.

`VerifiedTutor` asks the model, checks the reply, and if it fails asks once more, telling the
model which checks failed and why. If the repair fails too, or the call fails, times out or
returns something that isn't the JSON asked for, the template's wording is used. Both tries
share one time budget, so the worst wait is bounded.

Every try is reported as a `CheckRecord`, for the log and for the evaluation.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.tutor.base import NO_HISTORY, History, Tutor, TutorFeedback, TutorQuestion
from btl.tutor.foundry import FoundryTutor
from btl.tutor.model import ModelError, ModelReply
from btl.tutor.prompts import PROMPT_VERSION, Repair
from btl.tutor.slots import feedback_values, question_values, slotify
from btl.tutor.verifier import Check, FeedbackText, verify_feedback, verify_question

# Seconds for one question or feedback, repair included.
CALL_BUDGET = 12.0
# A repair isn't tried with less time than this left.
MIN_REPAIR_SECONDS = 1.0
TEMPLATE = "template"


@dataclass(frozen=True, slots=True)
class CheckRecord:
    """One try at wording something: what was asked, how it went, and what it cost.

    ``attempt`` is 1 for the first try and 2 for the repair. ``reasons`` are the failed checks'
    names; ``error`` says why there was no usable reply at all.
    """

    prompt_version: int
    kind: Literal["question", "feedback"]
    pack_id: str
    attempt: int
    passed: bool
    reasons: tuple[str, ...]
    error: str | None
    model: str | None
    seconds: float
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class Fallback:
    """The model was asked to word something, and the fallback's words were used instead.

    ``reasons`` are the last try's failed checks, or "no reply" when the call failed.
    """

    kind: Literal["question", "feedback"]
    pack_id: str
    concept: str
    reasons: tuple[str, ...]


def _ignore(_: CheckRecord | Fallback) -> None:
    pass


@dataclass
class VerifiedTutor:
    """A `btl.tutor.base.Tutor`: the model's wording if the Verifier passes it, else the fallback's.

    ``clock`` reads seconds; it is a parameter so tests can control the budget. ``on_fallback``
    hears each time the fallback's words are used.
    """

    primary: FoundryTutor
    fallback: Tutor
    on_check: Callable[[CheckRecord], None] = field(default=_ignore)
    budget: float = CALL_BUDGET
    clock: Callable[[], float] = field(default=time.monotonic)
    on_fallback: Callable[[Fallback], None] = field(default=_ignore)

    def question(self, view: QuestionView) -> TutorQuestion:
        """The model's question if it passes, else the fallback's."""
        plain = self.fallback.question(view)
        started = self.clock()
        repair: Repair | None = None
        reasons: tuple[str, ...] = ("no reply",)
        for attempt in (1, 2):
            timeout = self._left(started)
            if attempt == 2 and timeout < MIN_REPAIR_SECONDS:
                break
            try:
                worded = self.primary.word_question(view, plain.text, repair, timeout)
            except ModelError as error:
                self._failed("question", view.pack_id, attempt, error)
                reasons = ("no reply",)
                break
            text = slotify(worded.text, question_values(view))
            check = verify_question(text, view)
            self._record("question", view.pack_id, attempt, check, worded.reply)
            if check.passed:
                return TutorQuestion(text)
            repair = Repair(worded.reply.text, check.failures)
            reasons = check.reasons
        self.on_fallback(Fallback("question", view.pack_id, view.concept_name, reasons))
        return plain

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        """The model's feedback if it passes, else the fallback's, labelled with who wrote it."""
        plain = self.fallback.feedback(pack, grade, history)
        started = self.clock()
        repair: Repair | None = None
        reasons: tuple[str, ...] = ("no reply",)
        for attempt in (1, 2):
            timeout = self._left(started)
            if attempt == 2 and timeout < MIN_REPAIR_SECONDS:
                break
            try:
                worded = self.primary.word_feedback(pack, grade, plain, repair, timeout, history)
            except ModelError as error:
                self._failed("feedback", pack.pack_id, attempt, error)
                reasons = ("no reply",)
                break
            values = feedback_values(pack, grade.chosen)
            outcome = set(pack.outcome)
            text = FeedbackText(
                slotify(worded.feedback.explanation, values, outcome),
                slotify(worded.feedback.takeaway, values, outcome),
                worded.feedback.misconception,
            )
            check = verify_feedback(text, pack, grade)
            self._record("feedback", pack.pack_id, attempt, check, worded.reply)
            if check.passed:
                source = worded.reply.model + (" (repaired)" if attempt == 2 else "")
                return _feedback(text, pack, source)
            repair = Repair(worded.reply.text, check.failures)
            reasons = check.reasons
        self.on_fallback(Fallback("feedback", pack.pack_id, pack.concept.name, reasons))
        return TutorFeedback(
            explanation=plain.explanation,
            takeaway=plain.takeaway,
            source=f"{TEMPLATE} (fallback: {', '.join(reasons)})",
            misconception=plain.misconception,
        )

    def _left(self, started: float) -> float:
        return self.budget - (self.clock() - started)

    def _record(
        self,
        kind: Literal["question", "feedback"],
        pack_id: str,
        attempt: int,
        check: Check,
        reply: ModelReply,
    ) -> None:
        self.on_check(
            CheckRecord(
                PROMPT_VERSION,
                kind,
                pack_id,
                attempt,
                check.passed,
                check.reasons,
                None,
                reply.model,
                reply.seconds,
                reply.input_tokens,
                reply.output_tokens,
            )
        )

    def _failed(
        self, kind: Literal["question", "feedback"], pack_id: str, attempt: int, error: ModelError
    ) -> None:
        self.on_check(
            CheckRecord(
                PROMPT_VERSION, kind, pack_id, attempt, False, (), str(error), None, 0.0, 0, 0
            )
        )


def _feedback(text: FeedbackText, pack: EvidencePack, source: str) -> TutorFeedback:
    misconception = (
        None if text.misconception is None else pack.concept.misconceptions[text.misconception]
    )
    return TutorFeedback(text.explanation, text.takeaway, source, misconception)
