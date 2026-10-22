"""Evidence packs of every kind of question, from simulated matches, for Tutor tests."""

from collections.abc import Iterator
from functools import cache

import numpy as np

from btl.concepts.phase import PhaseOfPlay
from btl.league.league import generate_league
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import Delivered, EvidencePack, build_pack
from btl.learn.knowledge import Delivery
from btl.learn.questions import Asks, build_question
from tests.fixtures.learning import designed_with_candidates, threat_model

# Where a deferred question can be asked: at a stoppage, at half-time, or at full time.
DEFERRED = (
    Delivered(Delivery.DEFERRED, 1, 2000.0, PhaseOfPlay.DEAD_BALL, "goal kick"),
    Delivered(Delivery.DEFERRED, 1, 2700.0, PhaseOfPlay.HALF_TIME),
    Delivered(Delivery.DEFERRED, 2, 2700.0, PhaseOfPlay.FULL_TIME),
)


@cache
def every_kind(seed: int, per_concept: int = 2) -> tuple[EvidencePack, ...]:
    """A few moments of each concept, at every level, asked live and later."""
    _, ctx, candidates = designed_with_candidates(seed)
    league = generate_league(np.random.default_rng(0))
    concepts = dict.fromkeys(candidate.concept for candidate in candidates)
    built: list[EvidencePack] = []
    for concept in concepts:
        for candidate in [c for c in candidates if c.concept == concept][:per_concept]:
            live = Delivered(
                Delivery.LIVE, candidate.period_id, candidate.time_seconds, candidate.phase
            )
            for level in (1, 2, 3):
                for delivered in (live, *DEFERRED):
                    question = build_question(
                        candidate,
                        level,
                        delivered.delivery,
                        ctx,
                        threat_model(),
                        np.random.default_rng(level),
                    )
                    if question is not None:
                        built.append(
                            build_pack(
                                question, delivered, ctx, threat_model(), league, load_concept_map()
                            )
                        )
    return tuple(built)


def first_of(asks: Asks, seeds: Iterator[int] | None = None) -> EvidencePack:
    """The first pack that asks this, from the earliest seed that has one."""
    for seed in seeds or iter(range(40)):
        for pack in every_kind(seed):
            if pack.asks is asks:
                return pack
    raise LookupError(f"no pack asks {asks.value!r}")
