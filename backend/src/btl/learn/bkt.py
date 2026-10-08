"""Bayesian Knowledge Tracing (BKT): mastery as the probability the viewer knows a concept.

BKT treats each concept as a hidden yes-or-no: does the viewer understand it? It keeps that
probability and, after each answer, updates it in two steps:

1. **The answer.** A viewer who knows the concept answers correctly unless they slip; one who
   doesn't can still guess right. Bayes' rule weighs how likely this answer was each way.
2. **Learning.** The viewer has just seen the feedback, so there is a chance they learned the
   concept now, whatever they answered.

Four parameters drive it. ``prior``, ``learn`` and ``slip`` come from the concept map, by tier,
with per-concept overrides. ``guess`` comes from the question: with three options a pure guess
is right one time in three.

Because of step 2, a wrong answer can still raise mastery a little when it was already low;
the explanation sentence says so.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from btl.learn.concept_map import ConceptKey, ConceptMap, Thresholds
from btl.learn.knowledge import ConceptChange, Observation, Update

MODEL_NAME = "bkt"
MODEL_VERSION = 1


@dataclass(frozen=True, slots=True)
class BktParams:
    """One concept's parameters: probabilities, each strictly between 0 and 1."""

    prior: float
    learn: float
    slip: float

    def __post_init__(self) -> None:
        """Reject probabilities of exactly 0 or 1, which would make BKT stop learning."""
        for name in ("prior", "learn", "slip"):
            value: float = getattr(self, name)
            if not 0 < value < 1:
                raise ValueError(f"{name} must be strictly between 0 and 1, got {value}")


@dataclass(frozen=True, slots=True)
class BktState:
    """The probability the viewer knows each concept. Read-only by convention."""

    known: Mapping[ConceptKey, float]


@dataclass(frozen=True, slots=True)
class BktModel:
    """BKT with parameters from the concept map. A `btl.learn.knowledge.KnowledgeModel`."""

    concept_map: ConceptMap
    name: str = field(default=MODEL_NAME, init=False)
    version: int = field(default=MODEL_VERSION, init=False)

    @property
    def thresholds(self) -> Thresholds:
        """The map's thresholds for BKT."""
        return self.concept_map.learner_models[MODEL_NAME].thresholds

    def params(self, concept: ConceptKey) -> BktParams:
        """The concept's parameters: its tier's defaults, with its own overrides."""
        values = self.concept_map.model_parameters(MODEL_NAME, concept)
        return BktParams(prior=values["prior"], learn=values["learn"], slip=values["slip"])

    def initial_state(self, concepts: Collection[ConceptKey]) -> BktState:
        """Every concept at its prior."""
        return BktState({concept: self.params(concept).prior for concept in concepts})

    def mastery(self, state: BktState, concept: ConceptKey) -> float:
        """The probability the viewer knows the concept; its prior if it has no answers yet."""
        known = state.known.get(concept)
        return self.params(concept).prior if known is None else known

    def update(self, state: BktState, observation: Observation) -> tuple[BktState, Update]:
        """Bayes on the answer, then the chance of learning from the feedback.

        Each concept the question covers is updated on its own.

        Raises:
            ValueError: If a guess would be as likely to be right as an answer from someone who
                knows the concept, so the answer would say nothing.
        """
        guess = 1 / observation.options
        known = dict(state.known)
        changes: list[ConceptChange] = []
        for concept in observation.concepts:
            params = self.params(concept)
            if guess >= 1 - params.slip:
                raise ValueError(
                    f"{concept}: a guess ({guess:.2f}) is as likely right as knowing it "
                    f"({1 - params.slip:.2f}), so the answer says nothing"
                )
            before = self.mastery(state, concept)
            if observation.correct:
                if_known, if_not = before * (1 - params.slip), (1 - before) * guess
            else:
                if_known, if_not = before * params.slip, (1 - before) * (1 - guess)
            after_answer = if_known / (if_known + if_not)
            after = after_answer + (1 - after_answer) * params.learn
            known[concept] = after
            changes.append(
                ConceptChange(
                    concept=concept,
                    before=before,
                    after=after,
                    details={
                        "guess": guess,
                        "slip": params.slip,
                        "learn": params.learn,
                        "after answer": after_answer,
                    },
                )
            )
        return BktState(known), Update(observation, tuple(changes))

    def explain(self, update: Update) -> str:
        """Why each concept moved, in one sentence each, with the before and after numbers.

        For example: "Right. A guess is right 1 time in 3, and someone who understands
        line-breaking passes still slips 10% of the time, so we're now 42% sure you understand
        it, up from 15%."
        """
        return " ".join(
            _sentence(change, self._label(change.concept), update.observation)
            for change in update.changes
        )

    def _label(self, concept: ConceptKey) -> str:
        name = self.concept_map.concept(concept).name
        # "Line-breaking passes" reads as "line-breaking passes" mid-sentence; "xG" stays.
        return name[0].lower() + name[1:] if name[1:2].islower() else name


def _sentence(change: ConceptChange, label: str, observation: Observation) -> str:
    details = change.details
    before, after = _percent(change.before), _percent(change.after)
    slip, learn = _percent(details["slip"]), _percent(details["learn"])
    if observation.correct:
        return (
            f"Right. A guess is right 1 time in {observation.options}, and someone who "
            f"understands {label} still slips "
            f"{slip} of the time, so we're now {after} sure you understand it, up from {before}."
        )
    if change.after < change.before:
        return (
            f"Not this time. Someone who understands {label} slips only {slip} of the time, so "
            f"we're now {after} sure you understand it, down from {before}."
        )
    return (
        f"Not this time, which on its own lowers our estimate for {label}. But you've just seen "
        f"the explanation, and that teaches it {learn} of the time, so we're now {after} sure "
        f"you understand it, up from {before}."
    )


def _percent(probability: float) -> str:
    return f"{round(probability * 100)}%"
