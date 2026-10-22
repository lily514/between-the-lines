"""A fake model for end-to-end Tutor tests: it answers any request without the network."""

import json
import re
from dataclasses import dataclass, field

from btl.tutor.model import ModelReply, ModelRequest

QUESTION = "Over to you: what is your read on {team} here?"
TAKEAWAY = "Watch how {team} played it."
OUTCOME_LIST = "Facts that answer the question (outcome facts):\n{"


@dataclass
class ByKind:
    """Words every question the same way, and feedback from the first outcome fact it is sent.

    Its feedback cites ``{answer}`` and that fact, which passes the Verifier. Every
    ``fail_every``-th feedback (and its repair) gives a verdict instead, which fails, so both
    the model's words and the template's fallback get used.
    """

    model: str = "fake-model"
    fail_every: int = 3
    requests: list[ModelRequest] = field(default_factory=list[ModelRequest])
    _feedback: int = 0

    def complete(self, request: ModelRequest) -> ModelReply:
        self.requests.append(request)
        if request.schema_name == "question":
            text = json.dumps({"text": QUESTION})
        else:
            start = request.prompt.index(OUTCOME_LIST) + len(OUTCOME_LIST) - 1
            match = re.match(r"\{([\w.]+)\}", request.prompt[start:])
            assert match is not None
            repairing = "Your last reply was:" in request.prompt
            self._feedback += 0 if repairing else 1
            explanation = f"The answer was {{answer}}, and {{{match.group(1)}}} settles it."
            if self._feedback % self.fail_every == 0:
                explanation = "Well done: " + explanation
            text = json.dumps(
                {"explanation": explanation, "takeaway": TAKEAWAY, "misconception": None}
            )
        return ModelReply(text, self.model, 100, 20, 0.0)
