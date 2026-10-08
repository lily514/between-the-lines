"""The concept map: the curriculum of football concepts, read from ``concept_map.yaml``.

The YAML file is where the curriculum is written: each concept's tier, prerequisites,
explanations at three levels, misconceptions and the facts its explanations need, plus each
knowledge model's settings. This module is the only reader. It turns the file into frozen
dataclasses and checks every rule in the file's header comment, reporting all broken rules at
once so that an edit can be fixed in one go.
"""

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import NewType, cast

import yaml

from btl.schema.vocab import ConceptId

CONCEPT_MAP_FILE = "concept_map.yaml"
MAP_VERSION = 1
# Every match provides these, so explanations and prompts may use them without listing them.
MATCH_FIELDS = frozenset({"home_team", "away_team"})
DATA_REQUIREMENTS = frozenset({"events", "snapshot", "window"})
# CLAUDE.md's hard rule: no betting framing anywhere.
BETTING_WORDS = frozenset(
    {"bet", "bets", "betting", "bookmaker", "bookie", "odds", "punter", "stake", "stakes"}
    | {"tip", "tips", "wager", "wagers", "accumulator"}
)

ConceptKey = NewType("ConceptKey", str)

_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
_WORD = re.compile(r"[a-z]+")


class ConceptMapError(ValueError):
    """The concept map breaks one or more of its rules; the message lists each one."""

    def __init__(self, problems: Collection[str]) -> None:
        """Gather the problems into one message, one per line."""
        self.problems = tuple(problems)
        super().__init__("the concept map is invalid:\n" + "\n".join(f"- {p}" for p in problems))


@dataclass(frozen=True, slots=True)
class Thresholds:
    """When a concept unlocks the ones that need it, and when it counts as mastered."""

    unlock: float
    mastery: float


@dataclass(frozen=True, slots=True)
class LearnerModelSettings:
    """One knowledge model's settings: its thresholds and its parameters for each tier."""

    thresholds: Thresholds
    tier_defaults: Mapping[int, Mapping[str, float]]


@dataclass(frozen=True, slots=True)
class Tier:
    """A stage of the curriculum, from newcomer (0) to analyst (3)."""

    name: str
    goal: str


@dataclass(frozen=True, slots=True)
class Explanations:
    """Anchor text for one concept at each level, with ``{placeholders}`` for facts."""

    beginner: str
    intermediate: str
    analyst: str


@dataclass(frozen=True, slots=True)
class Concept:
    """One football concept: a knowledge component the learner model tracks.

    ``model_overrides`` holds parameters that replace a model's tier defaults for this concept,
    by model name.
    """

    key: ConceptKey
    name: str
    strand: str
    tier: int
    prerequisites: tuple[ConceptKey, ...]
    objective: str
    detector: ConceptId | None
    data_requirements: tuple[str, ...]
    question_types: tuple[str, ...]
    example_prompt: str
    explanations: Explanations
    misconceptions: tuple[str, ...]
    evidence_fields: tuple[str, ...]
    capstone: bool
    brief_links: tuple[str, ...]
    model_overrides: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True, slots=True)
class ConceptMap:
    """The whole curriculum. Concepts keep the file's order, which runs by tier."""

    version: int
    learner_models: Mapping[str, LearnerModelSettings]
    tiers: Mapping[int, Tier]
    strands: Mapping[str, str]
    question_types: Mapping[str, str]
    concepts: tuple[Concept, ...]

    def concept(self, key: ConceptKey) -> Concept:
        """The concept with this key.

        Raises:
            KeyError: If there is none.
        """
        for concept in self.concepts:
            if concept.key == key:
                return concept
        raise KeyError(key)

    def concept_for_detector(self, detector: ConceptId) -> Concept | None:
        """The concept a detector's tags are evidence for, if the map has one."""
        return next((c for c in self.concepts if c.detector is detector), None)

    def model_parameters(self, model: str, key: ConceptKey) -> Mapping[str, float]:
        """A model's parameters for one concept: its tier's defaults, then the concept's own."""
        concept = self.concept(key)
        defaults = self.learner_models[model].tier_defaults[concept.tier]
        return {**defaults, **concept.model_overrides.get(model, {})}

    def prerequisites_in_force(
        self, key: ConceptKey, active: Collection[ConceptKey]
    ) -> frozenset[ConceptKey]:
        """The active concepts this one waits for.

        A prerequisite that isn't active (nothing can ask about it yet) counts as met, but its
        own prerequisites still apply. So if a concept needs B, and B needs A, the concept waits
        for A whenever A is active and B isn't.
        """
        in_force: set[ConceptKey] = set()
        seen: set[ConceptKey] = set()
        waiting = list(self.concept(key).prerequisites)
        while waiting:
            prerequisite = waiting.pop()
            if prerequisite in seen:
                continue
            seen.add(prerequisite)
            if prerequisite in active:
                in_force.add(prerequisite)
            else:
                waiting.extend(self.concept(prerequisite).prerequisites)
        return frozenset(in_force)

    def frontier(
        self,
        mastery: Mapping[ConceptKey, float],
        active: Collection[ConceptKey],
        thresholds: Thresholds,
    ) -> tuple[ConceptKey, ...]:
        """The active concepts worth asking about now, in map order.

        A concept is on the frontier when it isn't mastered yet and every prerequisite in force
        is above the unlock threshold.

        Args:
            mastery: The viewer's mastery of every active concept, from 0 to 1.
            active: The concepts the app can ask about.
            thresholds: The knowledge model's thresholds.
        """
        return tuple(
            concept.key
            for concept in self.concepts
            if concept.key in active
            and mastery[concept.key] < thresholds.mastery
            and all(
                mastery[prerequisite] >= thresholds.unlock
                for prerequisite in self.prerequisites_in_force(concept.key, active)
            )
        )


@cache
def load_concept_map() -> ConceptMap:
    """The concept map shipped with the package.

    It is read once; the file is part of the installed package, like the code.

    Raises:
        ConceptMapError: If the file breaks any of its rules.
    """
    text = resources.files("btl.learn").joinpath(CONCEPT_MAP_FILE).read_text(encoding="utf-8")
    return parse_concept_map(text)


def parse_concept_map(text: str) -> ConceptMap:
    """Read and check a concept map written in YAML.

    Raises:
        ConceptMapError: If the text breaks any of the map's rules.
    """
    reader = _Reader()
    concept_map = reader.concept_map(cast(object, yaml.safe_load(text)))
    problems = [*reader.problems, *_check(concept_map)] if concept_map else reader.problems
    if problems or concept_map is None:
        raise ConceptMapError(problems)
    return concept_map


class _Reader:
    """Turns the parsed YAML into dataclasses, noting each value of the wrong type."""

    def __init__(self) -> None:
        self.problems: list[str] = []

    def concept_map(self, raw: object) -> ConceptMap | None:
        top = self._mapping(raw, "the file")
        version = self._int(top.get("version"), "version")
        models = self._mapping(top.get("learner_models"), "learner_models")
        tiers = self._mapping(top.get("tiers"), "tiers")
        concepts = self._list(top.get("concepts"), "concepts")
        concept_map = ConceptMap(
            version=version,
            learner_models={
                str(name): self._model(settings, f"learner_models.{name}")
                for name, settings in models.items()
            },
            tiers={
                self._int(number, "a tier number"): self._tier(tier, f"tiers.{number}")
                for number, tier in tiers.items()
            },
            strands=self._text_mapping(top.get("strands"), "strands"),
            question_types=self._text_mapping(top.get("question_types"), "question_types"),
            concepts=tuple(
                self._concept(raw, f"concept {i + 1}") for i, raw in enumerate(concepts)
            ),
        )
        return None if self.problems else concept_map

    def _model(self, raw: object, where: str) -> LearnerModelSettings:
        settings = self._mapping(raw, where)
        thresholds = self._mapping(settings.get("thresholds"), f"{where}.thresholds")
        defaults = self._mapping(settings.get("tier_defaults"), f"{where}.tier_defaults")
        return LearnerModelSettings(
            thresholds=Thresholds(
                unlock=self._float(thresholds.get("unlock"), f"{where}.thresholds.unlock"),
                mastery=self._float(thresholds.get("mastery"), f"{where}.thresholds.mastery"),
            ),
            tier_defaults={
                self._int(tier, f"{where}.tier_defaults key"): self._numbers(
                    values, f"{where}.tier_defaults.{tier}"
                )
                for tier, values in defaults.items()
            },
        )

    def _tier(self, raw: object, where: str) -> Tier:
        tier = self._mapping(raw, where)
        return Tier(
            self._str(tier.get("name"), f"{where}.name"), self._str(tier.get("goal"), where)
        )

    def _concept(self, raw: object, where: str) -> Concept:
        concept = self._mapping(raw, where)
        key = self._str(concept.get("id"), f"{where}.id")
        where = f"concept {key!r}"
        explanations = self._mapping(concept.get("explanations"), f"{where}.explanations")
        overrides = self._mapping(concept.get("learner_models", {}), f"{where}.learner_models")
        return Concept(
            key=ConceptKey(key),
            name=self._str(concept.get("name"), f"{where}.name"),
            strand=self._str(concept.get("strand"), f"{where}.strand"),
            tier=self._int(concept.get("tier"), f"{where}.tier"),
            prerequisites=tuple(
                ConceptKey(p) for p in self._strs(concept.get("prerequisites"), where)
            ),
            objective=self._str(concept.get("objective"), f"{where}.objective"),
            detector=self._detector(concept.get("detector"), f"{where}.detector"),
            data_requirements=self._strs(concept.get("data_requirements"), where),
            question_types=self._strs(concept.get("question_types"), where),
            example_prompt=self._str(concept.get("example_prompt"), f"{where}.example_prompt"),
            explanations=Explanations(
                beginner=self._str(explanations.get("beginner"), f"{where}.beginner"),
                intermediate=self._str(explanations.get("intermediate"), f"{where}.intermediate"),
                analyst=self._str(explanations.get("analyst"), f"{where}.analyst"),
            ),
            misconceptions=self._strs(concept.get("misconceptions"), where),
            evidence_fields=self._strs(concept.get("evidence_fields"), where),
            capstone=concept.get("capstone", False) is True,
            brief_links=self._strs(concept.get("brief_links", []), where),
            model_overrides={
                str(model): self._numbers(values, f"{where}.learner_models.{model}")
                for model, values in overrides.items()
            },
        )

    def _detector(self, raw: object, where: str) -> ConceptId | None:
        if raw is None:
            return None
        try:
            return ConceptId(self._str(raw, where))
        except ValueError:
            known = ", ".join(c.value for c in ConceptId)
            self.problems.append(f"{where}: {raw!r} is not a detector; known ones are {known}")
            return None

    def _mapping(self, raw: object, where: str) -> Mapping[object, object]:
        if isinstance(raw, dict):
            return cast(dict[object, object], raw)
        self.problems.append(f"{where}: expected a mapping, got {raw!r}")
        return {}

    def _list(self, raw: object, where: str) -> list[object]:
        if isinstance(raw, list):
            return cast(list[object], raw)
        self.problems.append(f"{where}: expected a list, got {raw!r}")
        return []

    def _str(self, raw: object, where: str) -> str:
        if isinstance(raw, str):
            return raw
        self.problems.append(f"{where}: expected text, got {raw!r}")
        return ""

    def _strs(self, raw: object, where: str) -> tuple[str, ...]:
        return tuple(self._str(item, where) for item in self._list(raw, where))

    def _int(self, raw: object, where: str) -> int:
        if isinstance(raw, int) and not isinstance(raw, bool):
            return raw
        self.problems.append(f"{where}: expected a whole number, got {raw!r}")
        return 0

    def _float(self, raw: object, where: str) -> float:
        if isinstance(raw, int | float) and not isinstance(raw, bool):
            return float(raw)
        self.problems.append(f"{where}: expected a number, got {raw!r}")
        return 0.0

    def _numbers(self, raw: object, where: str) -> Mapping[str, float]:
        return {
            str(name): self._float(value, f"{where}.{name}")
            for name, value in self._mapping(raw, where).items()
        }

    def _text_mapping(self, raw: object, where: str) -> Mapping[str, str]:
        return {
            str(name): self._str(text, f"{where}.{name}")
            for name, text in self._mapping(raw, where).items()
        }


def _check(concept_map: ConceptMap) -> list[str]:
    """Every rule the map breaks, beyond values of the wrong type."""
    problems: list[str] = []
    if concept_map.version != MAP_VERSION:
        problems.append(f"version is {concept_map.version}; this code reads {MAP_VERSION}")
    for name, model in concept_map.learner_models.items():
        problems += _check_model(name, model, concept_map)

    keys = [concept.key for concept in concept_map.concepts]
    problems += [f"concept {key!r} appears more than once" for key in _repeated(keys)]
    detectors = [c.detector for c in concept_map.concepts if c.detector is not None]
    problems += [f"detector '{d}' belongs to more than one concept" for d in _repeated(detectors)]
    known = set(keys)
    for concept in concept_map.concepts:
        problems += _check_concept(concept, concept_map, known)
    if not problems:
        problems += [f"prerequisites form a cycle: {cycle}" for cycle in _cycles(concept_map)]
    problems += _betting_words(concept_map)
    return problems


def _check_model(name: str, model: LearnerModelSettings, concept_map: ConceptMap) -> list[str]:
    problems: list[str] = []
    unlock, mastery = model.thresholds.unlock, model.thresholds.mastery
    if not 0 < unlock < mastery < 1:
        problems.append(f"learner_models.{name}: need 0 < unlock < mastery < 1")
    missing = sorted(set(concept_map.tiers) - set(model.tier_defaults))
    if missing:
        problems.append(f"learner_models.{name}.tier_defaults: no defaults for tiers {missing}")
    names = {tuple(sorted(values)) for values in model.tier_defaults.values()}
    if len(names) > 1:
        problems.append(f"learner_models.{name}.tier_defaults: tiers name different parameters")
    return problems


def _check_concept(concept: Concept, concept_map: ConceptMap, known: Collection[str]) -> list[str]:
    where = f"concept {concept.key!r}"
    problems: list[str] = []
    if concept.tier not in concept_map.tiers:
        problems.append(f"{where}: tier {concept.tier} is not one of the declared tiers")
    if concept.strand not in concept_map.strands:
        problems.append(f"{where}: strand {concept.strand!r} is not one of the declared strands")
    problems += [
        f"{where}: question type {kind!r} is not one of the declared types"
        for kind in concept.question_types
        if kind not in concept_map.question_types
    ]
    problems += [
        f"{where}: data requirement {need!r} is not one of {sorted(DATA_REQUIREMENTS)}"
        for need in concept.data_requirements
        if need not in DATA_REQUIREMENTS
    ]
    problems += [
        f"{where}: prerequisite {p!r} is not a concept in the map"
        for p in concept.prerequisites
        if p not in known
    ]
    allowed = set(concept.evidence_fields) | MATCH_FIELDS
    texts = (
        concept.example_prompt,
        concept.explanations.beginner,
        concept.explanations.intermediate,
        concept.explanations.analyst,
    )
    problems += [
        f"{where}: placeholder {{{field}}} is not in its evidence_fields"
        for text in texts
        for field in _PLACEHOLDER.findall(text)
        if field not in allowed
    ]
    for model, values in concept.model_overrides.items():
        settings = concept_map.learner_models.get(model)
        if settings is None:
            problems.append(f"{where}: overrides an unknown model {model!r}")
            continue
        names = {name for defaults in settings.tier_defaults.values() for name in defaults}
        problems += [
            f"{where}: {model} has no parameter {name!r}" for name in values if name not in names
        ]
    return problems


def _repeated(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    repeated: list[str] = []
    for item in items:
        if item in seen and item not in repeated:
            repeated.append(item)
        seen.add(item)
    return repeated


def _cycles(concept_map: ConceptMap) -> list[str]:
    """Each prerequisite cycle, written as ``a -> b -> a``."""
    cycles: list[str] = []
    finished: set[ConceptKey] = set()

    def visit(key: ConceptKey, path: list[ConceptKey]) -> None:
        if key in path:
            loop = [*path[path.index(key) :], key]
            cycles.append(" -> ".join(loop))
            return
        if key in finished:
            return
        for prerequisite in concept_map.concept(key).prerequisites:
            visit(prerequisite, [*path, key])
        finished.add(key)

    for concept in concept_map.concepts:
        visit(concept.key, [])
    return cycles


def _betting_words(concept_map: ConceptMap) -> list[str]:
    texts = [
        *concept_map.strands.values(),
        *concept_map.question_types.values(),
        *(f"{tier.name} {tier.goal}" for tier in concept_map.tiers.values()),
    ]
    for concept in concept_map.concepts:
        texts += [concept.name, concept.objective, concept.example_prompt]
        texts += [concept.explanations.beginner, concept.explanations.intermediate]
        texts += [concept.explanations.analyst, *concept.misconceptions, *concept.brief_links]
    found = sorted({word for text in texts for word in _WORD.findall(text.lower())} & BETTING_WORDS)
    return [f"betting word {word!r} appears in the map" for word in found]
