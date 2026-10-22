"""The model's Tutor: it sends the prompts and reads the replies, but checks nothing.

`FoundryTutor` turns a question view or a pack into a request, sends it, and parses the JSON
reply. Whether the words may be shown is the Verifier's decision, made by
`btl.tutor.verified.VerifiedTutor`, which also asks for a repair and falls back to the
template. A reply that isn't the JSON asked for is a `ModelError`, like a failed call.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from btl.learn.evidence import EvidencePack, QuestionView
from btl.learn.grader import Grade
from btl.tutor.model import ModelClient, ModelError, ModelReply
from btl.tutor.prompts import Repair, feedback_request, question_request
from btl.tutor.verifier import FeedbackText


@dataclass(frozen=True, slots=True)
class WordedQuestion:
    """A question's wording from the model, and the reply it came in."""

    text: str
    reply: ModelReply


@dataclass(frozen=True, slots=True)
class WordedFeedback:
    """Feedback's wording from the model, and the reply it came in."""

    feedback: FeedbackText
    reply: ModelReply


@dataclass(frozen=True, slots=True)
class FoundryTutor:
    """Words questions and feedback with a model, through any `ModelClient`."""

    client: ModelClient

    def word_question(
        self, view: QuestionView, plain: str, repair: Repair | None = None
    ) -> WordedQuestion:
        """The model's wording of a question.

        Raises:
            ModelError: If the call fails or the reply isn't ``{"text": ...}``.
        """
        reply = self.client.complete(question_request(view, plain, repair))
        fields = _fields(reply)
        return WordedQuestion(_text(fields, "text"), reply)

    def word_feedback(
        self, pack: EvidencePack, grade: Grade, repair: Repair | None = None
    ) -> WordedFeedback:
        """The model's feedback after an answer.

        Raises:
            ModelError: If the call fails or the reply isn't the feedback's JSON.
        """
        reply = self.client.complete(feedback_request(pack, grade, repair))
        fields = _fields(reply)
        misconception = fields.get("misconception")
        if misconception is not None and (
            not isinstance(misconception, int) or isinstance(misconception, bool)
        ):
            raise ModelError(f"misconception should be a number or null, not {misconception!r}")
        feedback = FeedbackText(
            _text(fields, "explanation"), _text(fields, "takeaway"), misconception
        )
        return WordedFeedback(feedback, reply)


def _fields(reply: ModelReply) -> Mapping[str, object]:
    try:
        parsed: object = json.loads(reply.text)
    except json.JSONDecodeError as error:
        raise ModelError(f"the reply isn't JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise ModelError("the reply isn't a JSON object")
    return cast(dict[str, object], parsed)


def _text(fields: Mapping[str, object], name: str) -> str:
    value = fields.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ModelError(f"{name} should be text, not {value!r}")
    return value.strip()
