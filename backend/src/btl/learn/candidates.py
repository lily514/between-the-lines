"""Candidate moments: every moment in a match worth asking about, found by the detectors alone.

Every match is simulated from the same `MATCH_DESIGN`, whoever watches it, so the match never
depends on the viewer. Planting is only a stand-in for "a real match has plenty of good
moments". Candidates come from the detectors, never from the match's planting records, so this
would work unchanged on a real match: planted moments are simply candidates the detectors are
sure to find.

A detector's rule says what a concept *is*; a quality rule here says which occurrences are
good enough to *teach* with. Both are written in football terms.
"""

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum

from btl.concepts.base import ConceptTag, Detector, MatchContext
from btl.concepts.phase import PhaseOfPlay, PhaseTimeline
from btl.concepts.registry import ALL_DETECTORS, detect_all
from btl.league.league import Club
from btl.learn.concept_map import ConceptKey, ConceptMap
from btl.plant.planter import Planter
from btl.plant.spec import LEVELS, MomentSpec, PlantRequest
from btl.schema.match import Match
from btl.schema.vocab import ConceptId
from btl.sim.engine import simulate_match

# Each concept that can be planted, at every level, in every match.
MATCH_DESIGN = PlantRequest(
    tuple(
        MomentSpec(concept, level)
        for concept in (ConceptId.LINE_BREAKING_PASS, ConceptId.COUNTER_PRESS)
        for level in LEVELS
    )
)
# A line-breaking pass worth teaching goes clearly forward. The simulator's flat lines make
# many 9-11 m passes between two level midfielders count as breaking a line, which is correct
# but shows little. Planted ones go 14 m forward.
MIN_FORWARD = 12.0


def play_designed_match(home: Club, away: Club, seed: int) -> Match:
    """Simulate a match to `MATCH_DESIGN`, planting as many of its moments as fit.

    Unlike `btl.plant.planter.simulate_with_moments`, a moment that finds no room before the
    whistle is simply left out (about 1 match in 100): planting only stands in for a real
    match's good moments, and the learning loop takes whatever the detectors find.
    """
    return simulate_match(home, away, seed, director=Planter(MATCH_DESIGN))


class AskedWhen(StrEnum):
    """When a moment may be asked about."""

    # Live if play is settled; otherwise reviewed at a later stoppage or break.
    IN_PLAY = "in play"
    # Live in the dead ball straight after it, or never: a restart or a foul that stops play.
    AT_THE_STOPPAGE = "at the stoppage"
    # Only ever reviewed later: play went on, as after advantage.
    AFTERWARDS = "afterwards"


@dataclass(frozen=True, slots=True)
class Candidate:
    """A moment the learning loop could ask about.

    ``phase`` is the phase of play at the tag's key action. With ``asked_when``, it decides
    when the question can be asked.
    """

    concept: ConceptKey
    tag: ConceptTag
    difficulty: float
    phase: PhaseOfPlay
    period_id: int
    time_seconds: float
    asked_when: AskedWhen = AskedWhen.IN_PLAY


def find_candidates(
    ctx: MatchContext,
    timeline: PhaseTimeline,
    concept_map: ConceptMap,
    active: Collection[ConceptKey],
) -> tuple[Candidate, ...]:
    """Every moment of the active concepts that is good enough to teach with, in match order.

    Args:
        ctx: The match as detectors see it. It needs threat values.
        timeline: The match's phases of play.
        concept_map: Says which detector finds each concept.
        active: The concepts the app can ask about.

    Raises:
        ValueError: If the context has no threat values, or an active concept's detector
            gives no difficulty.
    """
    if ctx.threat is None:
        raise ValueError("finding candidates needs threat values; pass them to match_context")
    detectors = _detectors(concept_map, active)
    candidates: list[Candidate] = []
    for tag in detect_all(ctx, detectors):
        worth_teaching = WORTH_TEACHING.get(tag.concept)
        if worth_teaching is not None and not worth_teaching(tag, ctx):
            continue
        concept = concept_map.concept_for_detector(tag.concept)
        if concept is None or tag.difficulty is None:
            raise ValueError(f"{tag.concept} is active but its detector gives no difficulty")
        event = ctx.events[tag.action_id]
        asked_when = ASKED_WHEN.get(tag.concept)
        candidates.append(
            Candidate(
                concept=concept.key,
                tag=tag,
                difficulty=tag.difficulty,
                phase=timeline.phase_of(tag.action_id),
                period_id=event.period_id,
                time_seconds=event.time_seconds,
                asked_when=AskedWhen.IN_PLAY if asked_when is None else asked_when(tag),
            )
        )
    return tuple(candidates)


def _detectors(concept_map: ConceptMap, active: Collection[ConceptKey]) -> tuple[Detector, ...]:
    wanted = {concept_map.concept(key).detector for key in active}
    return tuple(detector for detector in ALL_DETECTORS if detector.concept in wanted)


def _clearly_forward_and_threatening(tag: ConceptTag, ctx: MatchContext) -> bool:
    event = ctx.events[tag.action_id]
    threat = ctx.threat[tag.action_id] if ctx.threat else None
    return event.end_x - event.start_x >= MIN_FORWARD and threat is not None and threat > 0


# The quality rule for each concept that has one; every other tag is worth teaching.
WORTH_TEACHING: Mapping[ConceptId, Callable[[ConceptTag, MatchContext], bool]] = {
    ConceptId.LINE_BREAKING_PASS: _clearly_forward_and_threatening,
}


def _after_a_foul(tag: ConceptTag) -> AskedWhen:
    return AskedWhen.AFTERWARDS if tag.evidence["advantage"] else AskedWhen.AT_THE_STOPPAGE


# When each concept's moments may be asked, for those not asked in play.
ASKED_WHEN: Mapping[ConceptId, Callable[[ConceptTag], AskedWhen]] = {
    ConceptId.RESTART: lambda tag: AskedWhen.AT_THE_STOPPAGE,
    ConceptId.FOUL: _after_a_foul,
}
