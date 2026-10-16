import json
from typing import cast

import numpy as np
import pytest

from btl.api.payloads import question_payload
from btl.concepts.phase import PhaseOfPlay
from btl.league.league import generate_league
from btl.learn.candidates import Candidate
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import Delivered, EvidencePack, build_pack, question_view
from btl.learn.knowledge import Delivery
from btl.learn.questions import Form, build_question
from btl.learn.selector import Prompt
from btl.learn.session import Asked
from btl.schema.vocab import ConceptId
from tests.fixtures.learning import designed_with_candidates, threat_model

OUTCOME_NAMES = {
    "lines_broken",
    "gap_m",
    "xt_before",
    "xt_after",
    "threat_added",
    "receiver",
    "receiver_zone",
    "seconds_to_regain",
    "metres_from_goal",
    "pressers",
}
HIDDEN = {
    "correct",
    "correct_key",
    "outcome",
    "reveal_path",
    "reveal_line",
    "chosen",
    "explanation",
}
ASKED_LATER = Delivered(Delivery.DEFERRED, 1, 2000.0, PhaseOfPlay.DEAD_BALL, "goal kick")


def asked_for(candidate: Candidate, level: int, delivery: Delivery, seed: int) -> Asked | None:
    match, ctx, _ = designed_with_candidates(seed)
    question = build_question(
        candidate, level, delivery, ctx, threat_model(), np.random.default_rng(0)
    )
    if question is None:
        return None
    delivered = Delivered(delivery, candidate.period_id, candidate.time_seconds, candidate.phase)
    if delivery is Delivery.DEFERRED:
        delivered = ASKED_LATER
    pack = build_pack(
        question,
        delivered,
        ctx,
        threat_model(),
        generate_league(np.random.default_rng(0)),
        load_concept_map(),
    )
    prompt = Prompt(candidate, level, delivered)
    return Asked(pack, question_view(pack), "Where now?", match, prompt)


def keys_in(value: object) -> set[str]:
    """Every key at any depth of parsed JSON."""
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        return set(mapping) | {key for child in mapping.values() for key in keys_in(child)}
    if isinstance(value, list):
        return {key for item in cast(list[object], value) for key in keys_in(item)}
    return set()


def threat_displays(pack: EvidencePack) -> set[str]:
    """Threat figures, which are distinctive enough to search for in the payload's text."""
    facts = [*pack.outcome.values()] + [f for o in pack.options for f in o.outcome.values()]
    return {fact.display for fact in facts if "%" in fact.display}


@pytest.mark.parametrize("seed", range(40))
def test_a_question_payload_never_holds_the_answer_or_an_outcome(seed: int) -> None:
    _, _, candidates = designed_with_candidates(seed)
    for concept in (ConceptId.LINE_BREAKING_PASS, ConceptId.COUNTER_PRESS):
        for candidate in [c for c in candidates if c.tag.concept is concept][:2]:
            for level in (1, 2, 3):
                for delivery in Delivery:
                    asked = asked_for(candidate, level, delivery, seed)
                    if asked is None:
                        continue
                    payload = question_payload(asked, 1, "Home", "Away")
                    text = payload.model_dump_json()
                    names = keys_in(json.loads(text))

                    assert not names & OUTCOME_NAMES
                    assert not names & HIDDEN
                    assert not any(display in text for display in threat_displays(asked.pack))
                    if asked.pack.form is Form.PREDICT:
                        assert payload.picture.path == []


def test_a_question_payload_says_when_the_moment_happened_and_when_it_is_asked() -> None:
    _, _, candidates = designed_with_candidates(0)
    candidate = next(c for c in candidates if c.tag.concept is ConceptId.COUNTER_PRESS)
    asked = asked_for(candidate, 1, Delivery.DEFERRED, 0)
    assert asked is not None

    payload = question_payload(asked, 2, "Home", "Away")

    assert payload.occurred.period == candidate.period_id
    assert payload.occurred.seconds == candidate.time_seconds
    assert payload.occurred.clock == asked.pack.timing.occurred_at
    assert payload.delivered.delivery == "deferred"
    assert (payload.delivered.period, payload.delivered.seconds) == (1, 2000.0)
    assert payload.delivered.clock == "33:20"
    assert (payload.delivered.phase, payload.delivered.restart) == ("dead ball", "goal kick")
    assert (payload.match_number, payload.home, payload.away) == (2, "Home", "Away")
