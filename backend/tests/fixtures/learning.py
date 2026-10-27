"""Simulated matches for learning-loop tests, built once per test run and shared."""

from functools import cache

import numpy as np

from btl.concepts.base import MatchContext, match_context
from btl.concepts.phase import phase_timeline
from btl.league.league import generate_league
from btl.learn.candidates import Candidate, find_candidates, play_designed_match
from btl.learn.concept_map import ConceptKey, load_concept_map
from btl.schema.match import Match
from btl.value.xt import ThreatModel, fit_on_simulated_matches, rate_match

LINE_BREAKING = ConceptKey("line_breaking_pass")
COUNTER_PRESS = ConceptKey("counter_press")
RESTARTS = ConceptKey("restarts")
OFFSIDE = ConceptKey("offside")
FOULS = ConceptKey("fouls_and_cards")
TRANSITIONS = ConceptKey("transitions")
TACKLES = ConceptKey("tackles")
ACTIVE = (TACKLES, RESTARTS, OFFSIDE, FOULS, LINE_BREAKING, COUNTER_PRESS)


@cache
def threat_model() -> ThreatModel:
    return fit_on_simulated_matches(generate_league(np.random.default_rng(0)), 0, 20, seed=0)


@cache
def designed(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return play_designed_match(home, away, seed)


def context(match: Match) -> MatchContext:
    return match_context(match, rate_match(threat_model(), match))


def candidates_in(match: Match, active: tuple[ConceptKey, ...] = ACTIVE) -> tuple[Candidate, ...]:
    return find_candidates(context(match), phase_timeline(match), load_concept_map(), active)


@cache
def designed_with_candidates(seed: int) -> tuple[Match, MatchContext, tuple[Candidate, ...]]:
    match = designed(seed)
    return match, context(match), candidates_in(match)
