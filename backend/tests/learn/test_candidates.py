import ast
import inspect
from dataclasses import replace

import numpy as np
import pytest

from btl.concepts.base import match_context
from btl.concepts.phase import PhaseOfPlay, phase_timeline
from btl.learn import candidates as candidates_module
from btl.learn.candidates import Candidate, find_candidates
from btl.learn.concept_map import load_concept_map
from btl.schema.vocab import ConceptId
from tests.fixtures.concepts import BACK_LINE, MIDFIELD_LINE, Spot, one_pass
from tests.fixtures.learning import ACTIVE, COUNTER_PRESS, LINE_BREAKING, candidates_in, designed

# The selector's difficulty band for each question level.
BANDS = {1: (0.0, 0.4), 2: (0.3, 0.7), 3: (0.6, 1.0)}


def one_pass_candidates(start: Spot, end: Spot, threat: float) -> tuple[Candidate, ...]:
    match = one_pass(start, end, MIDFIELD_LINE + BACK_LINE)
    ctx = match_context(match, (threat,))
    return find_candidates(ctx, phase_timeline(match), load_concept_map(), ACTIVE)


def test_a_clearly_forward_line_breaking_pass_that_adds_threat_is_a_candidate() -> None:
    (candidate,) = one_pass_candidates((40, 34), (60, 34), threat=0.01)

    assert candidate.concept == LINE_BREAKING
    assert candidate.difficulty == candidate.tag.difficulty
    assert candidate.phase is PhaseOfPlay.SETTLED


def test_a_short_line_breaking_pass_teaches_too_little() -> None:
    assert one_pass_candidates((44, 34), (55, 34), threat=0.01) == ()


def test_a_line_breaking_pass_that_adds_no_threat_teaches_too_little() -> None:
    assert one_pass_candidates((40, 34), (60, 34), threat=-0.001) == ()


def test_candidates_need_threat_values() -> None:
    match = one_pass((40, 34), (60, 34), MIDFIELD_LINE)

    with pytest.raises(ValueError, match="needs threat values"):
        find_candidates(match_context(match), phase_timeline(match), load_concept_map(), ACTIVE)


@pytest.mark.parametrize("seed", range(6))
def test_every_planted_moment_is_a_candidate(seed: int) -> None:
    match = designed(seed)
    found = {(c.tag.concept, c.tag.action_id) for c in candidates_in(match)}

    assert len(match.planted) == 6
    assert all((m.concept, m.answer_action_id) in found for m in match.planted)


@pytest.mark.parametrize("seed", range(3))
def test_candidates_are_the_same_without_the_planting_records(seed: int) -> None:
    match = designed(seed)

    assert candidates_in(replace(match, planted=())) == candidates_in(match)


def test_the_candidate_finder_never_reads_planting_records() -> None:
    tree = ast.parse(inspect.getsource(candidates_module))

    reads = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute)]

    assert not [node.attr for node in reads if node.attr == "planted"]


def test_only_active_concepts_give_candidates_in_match_order() -> None:
    every = candidates_in(designed(0))
    presses = candidates_in(designed(0), (COUNTER_PRESS,))

    assert {c.concept for c in every} == set(ACTIVE)
    assert {c.tag.concept for c in presses} == {ConceptId.COUNTER_PRESS}
    assert [c.tag.action_id for c in every] == sorted(c.tag.action_id for c in every)


def test_natural_settled_line_breaks_are_plentiful_at_levels_two_and_three() -> None:
    counts: dict[int, list[int]] = {level: [] for level in BANDS}
    for seed in range(40):
        match = designed(seed)
        planted = {m.answer_action_id for m in match.planted}
        settled = [
            c
            for c in candidates_in(match, (LINE_BREAKING,))
            if c.phase is PhaseOfPlay.SETTLED and c.tag.action_id not in planted
        ]
        for level, (low, high) in BANDS.items():
            counts[level].append(sum(low <= c.difficulty <= high for c in settled))

    # Measured over these 40 seeds: level 1 median 1 (often 0), level 2 at least 7 (median
    # 15), level 3 at least 22 (median 33). Level 1 is rare because natural gaps are rarely
    # wider than 14 m; level-1 questions are identify questions, which the planted level-1
    # moment can also supply as a deferred review.
    assert min(counts[2]) >= 5
    assert min(counts[3]) >= 15
    assert float(np.median(counts[1])) <= 3
