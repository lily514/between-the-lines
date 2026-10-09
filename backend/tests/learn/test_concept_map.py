import copy
from collections.abc import Callable
from typing import cast

import pytest
import yaml

from btl.learn.concept_map import (
    ConceptKey,
    ConceptMap,
    ConceptMapError,
    Thresholds,
    load_concept_map,
    parse_concept_map,
)
from btl.schema.vocab import ConceptId

THRESHOLDS = Thresholds(unlock=0.8, mastery=0.95)
A, B, C = ConceptKey("a"), ConceptKey("b"), ConceptKey("c")

Raw = dict[str, object]


def concept(key: str, tier: int, prerequisites: list[str], **extra: object) -> Raw:
    return {
        "id": key,
        "name": key.title(),
        "strand": "possession",
        "tier": tier,
        "prerequisites": prerequisites,
        "objective": "Spot it.",
        "detector": None,
        "data_requirements": ["events"],
        "question_types": ["identify"],
        "example_prompt": "Did {home_team} do it?",
        "explanations": {
            "beginner": "Plain words.",
            "intermediate": "{team} did it.",
            "analyst": "{team} did it {count} times.",
        },
        "misconceptions": ["A common mix-up."],
        "evidence_fields": ["team", "count"],
        **extra,
    }


def small_map() -> Raw:
    """A valid three-concept chain: a (tier 0) <- b (tier 1) <- c (tier 2)."""
    return {
        "version": 1,
        "learner_models": {
            "bkt": {
                "thresholds": {"unlock": 0.8, "mastery": 0.95},
                "tier_defaults": {
                    tier: {"prior": 0.2, "learn": 0.2, "slip": 0.1} for tier in (0, 1, 2)
                },
            }
        },
        "tiers": {tier: {"name": f"Tier {tier}", "goal": "Learn."} for tier in (0, 1, 2)},
        "strands": {"possession": "Keeping the ball."},
        "question_types": {"identify": "Recognise it.", "predict": "Say what happens next."},
        "concepts": [
            concept("a", 0, []),
            concept("b", 1, ["a"]),
            concept("c", 2, ["b"], detector="line_breaking_pass"),
        ],
    }


def parse(raw: Raw) -> ConceptMap:
    return parse_concept_map(yaml.safe_dump(raw))


def concepts_of(raw: Raw) -> list[Raw]:
    return cast(list[Raw], raw["concepts"])


def child(node: object, step: str | int) -> object:
    if isinstance(node, dict):
        return cast(dict[object, object], node)[step]
    return cast(list[object], node)[cast(int, step)]


def test_the_shipped_map_loads_and_keeps_its_rules() -> None:
    concept_map = load_concept_map()

    assert len(concept_map.concepts) == 18
    assert set(concept_map.tiers) == {0, 1, 2, 3}
    assert {c.detector for c in concept_map.concepts if c.detector} == {
        ConceptId.LINE_BREAKING_PASS,
        ConceptId.COUNTER_PRESS,
        ConceptId.COUNTER_ATTACK,
    }


def test_each_detector_leads_to_its_concept() -> None:
    concept_map = load_concept_map()

    line_breaking = concept_map.concept_for_detector(ConceptId.LINE_BREAKING_PASS)
    counter_press = concept_map.concept_for_detector(ConceptId.COUNTER_PRESS)

    assert line_breaking is not None and line_breaking.key == "line_breaking_pass"
    assert counter_press is not None and counter_press.prerequisites == ("pressing",)
    assert concept_map.concept_for_detector(ConceptId.SWITCH_OF_PLAY) is None


def test_a_new_viewer_starts_on_both_active_concepts_in_the_shipped_map() -> None:
    concept_map = load_concept_map()
    active = {ConceptKey("line_breaking_pass"), ConceptKey("counter_press")}
    settings = concept_map.learner_models["bkt"]
    priors = {key: concept_map.model_parameters("bkt", key)["prior"] for key in active}

    assert concept_map.frontier(priors, active, settings.thresholds) == tuple(
        c.key for c in concept_map.concepts if c.key in active
    )


def test_model_parameters_are_the_tier_defaults_with_the_concepts_overrides() -> None:
    raw = small_map()
    concepts_of(raw)[1]["learner_models"] = {"bkt": {"prior": 0.5}}
    concept_map = parse(raw)

    assert concept_map.model_parameters("bkt", A) == {"prior": 0.2, "learn": 0.2, "slip": 0.1}
    assert concept_map.model_parameters("bkt", B) == {"prior": 0.5, "learn": 0.2, "slip": 0.1}


def test_prerequisites_that_are_not_active_count_as_met() -> None:
    concept_map = parse(small_map())

    assert concept_map.frontier({C: 0.1}, {C}, THRESHOLDS) == (C,)


def test_a_concept_waits_for_an_active_prerequisite_behind_an_inactive_one() -> None:
    concept_map = parse(small_map())
    active = {A, C}

    assert concept_map.prerequisites_in_force(C, active) == {A}
    assert concept_map.frontier({A: 0.5, C: 0.1}, active, THRESHOLDS) == (A,)
    assert concept_map.frontier({A: 0.85, C: 0.1}, active, THRESHOLDS) == (A, C)


def test_mastered_concepts_leave_the_frontier() -> None:
    concept_map = parse(small_map())
    active = {A, B, C}

    assert concept_map.frontier({A: 0.96, B: 0.9, C: 0.1}, active, THRESHOLDS) == (B, C)
    assert concept_map.frontier({A: 0.96, B: 0.97, C: 0.97}, active, THRESHOLDS) == ()


def set_path(*path: str | int, value: object) -> Callable[[Raw], None]:
    def mutate(raw: Raw) -> None:
        target: object = raw
        for step in path[:-1]:
            target = child(target, step)
        if isinstance(target, dict):
            cast(dict[object, object], target)[path[-1]] = value
        else:
            cast(list[object], target)[cast(int, path[-1])] = value

    return mutate


def drop_tier_defaults(tier: int) -> Callable[[Raw], None]:
    def mutate(raw: Raw) -> None:
        defaults = child(child(child(raw, "learner_models"), "bkt"), "tier_defaults")
        del cast(dict[object, object], defaults)[tier]

    return mutate


BROKEN: list[tuple[str, Callable[[Raw], None], str]] = [
    ("wrong version", set_path("version", value=2), "version is 2"),
    (
        "unlock above mastery",
        set_path("learner_models", "bkt", "thresholds", "unlock", value=0.99),
        "need 0 < unlock < mastery < 1",
    ),
    (
        "a tier without defaults",
        drop_tier_defaults(2),
        "no defaults for tiers [2]",
    ),
    ("a repeated id", set_path("concepts", 1, "id", value="a"), "'a' appears more than once"),
    ("an unknown prerequisite", set_path("concepts", 1, "prerequisites", value=["z"]), "'z'"),
    ("a cycle", set_path("concepts", 0, "prerequisites", value=["c"]), "a -> c -> b -> a"),
    ("an unknown tier", set_path("concepts", 0, "tier", value=7), "tier 7"),
    ("an unknown strand", set_path("concepts", 0, "strand", value="vibes"), "'vibes'"),
    (
        "an unknown question type",
        set_path("concepts", 0, "question_types", value=["evaluate"]),
        "'evaluate'",
    ),
    (
        "an unknown data requirement",
        set_path("concepts", 0, "data_requirements", value=["tracking"]),
        "'tracking'",
    ),
    (
        "a placeholder without an evidence field",
        set_path("concepts", 0, "explanations", "analyst", value="{team} made {passes}."),
        "{passes}",
    ),
    ("an unknown detector", set_path("concepts", 0, "detector", value="dribble"), "'dribble'"),
    (
        "two concepts with one detector",
        set_path("concepts", 0, "detector", value="line_breaking_pass"),
        "more than one concept",
    ),
    (
        "an override of an unknown parameter",
        set_path("concepts", 0, "learner_models", value={"bkt": {"forget": 0.1}}),
        "no parameter 'forget'",
    ),
    (
        "a betting word",
        set_path("concepts", 0, "objective", value="Spot the odds."),
        "betting word 'odds'",
    ),
    ("text where a number belongs", set_path("concepts", 0, "tier", value="zero"), "tier"),
]


@pytest.mark.parametrize(("change", "mutate", "message"), BROKEN, ids=[b[0] for b in BROKEN])
def test_a_map_that_breaks_a_rule_is_rejected(
    change: str, mutate: Callable[[Raw], None], message: str
) -> None:
    raw = copy.deepcopy(small_map())
    mutate(raw)

    with pytest.raises(ConceptMapError) as error:
        parse(raw)

    assert any(message in problem for problem in error.value.problems), error.value.problems


def test_every_broken_rule_is_reported_at_once() -> None:
    raw = small_map()
    concepts_of(raw)[0]["strand"] = "vibes"
    concepts_of(raw)[2]["prerequisites"] = ["z"]

    with pytest.raises(ConceptMapError) as error:
        parse(raw)

    assert len(error.value.problems) == 2


def test_the_match_fields_need_no_evidence_field() -> None:
    raw = small_map()
    concepts_of(raw)[0]["example_prompt"] = "{home_team} against {away_team}: who has the ball?"

    assert parse(raw).concept(A).example_prompt.startswith("{home_team}")
