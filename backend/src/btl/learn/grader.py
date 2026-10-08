"""Grading: whether an answer is right.

An answer is tagged by kind, so other kinds can join later, such as free text graded by a
model. The knowledge models only ever see whether it was right.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from btl.learn.evidence import EvidencePack

VERDICTS = {True: "Spot on.", False: "Not quite."}


@dataclass(frozen=True, slots=True)
class ChoiceAnswer:
    """The option the viewer picked, by its key."""

    key: str
    kind: Literal["choice"] = field(default="choice", init=False)


# Free-text answers join this union when they arrive.
Answer = ChoiceAnswer


@dataclass(frozen=True, slots=True)
class Grade:
    """Whether an answer was right. ``chosen`` is the picked option's key, if there is one."""

    correct: bool
    chosen: str | None

    @property
    def verdict(self) -> str:
        """The opening word of the feedback, written by code so it can never contradict."""
        return VERDICTS[self.correct]


class Grader(Protocol):
    """Grades one kind of answer against the evidence pack."""

    def grade(self, pack: EvidencePack, answer: Answer) -> Grade:
        """Whether the answer is right."""
        ...


@dataclass(frozen=True, slots=True)
class ChoiceGrader:
    """Grades a picked option: right when it is the pack's correct one."""

    def grade(self, pack: EvidencePack, answer: Answer) -> Grade:
        """Compare the picked key with the pack's correct key.

        Raises:
            ValueError: If no option has that key.
        """
        keys = [option.key for option in pack.options]
        if answer.key not in keys:
            raise ValueError(f"no option {answer.key!r}; the options are {', '.join(keys)}")
        return Grade(correct=answer.key == pack.correct_key, chosen=answer.key)
