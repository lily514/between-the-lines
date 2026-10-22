"""Sample evidence packs of every kind of question, for measuring how a Tutor words them.

Packs come from the course's own matches, as viewers would meet them: each concept's moments,
at every level, asked live and at a later stoppage. `balanced` then keeps a few of each kind of
question, level and delivery, so rare kinds (why a player was booked) aren't drowned out by
common ones (what restart).
"""

from collections.abc import Iterable, Sequence

import numpy as np

from btl.concepts.phase import PhaseOfPlay
from btl.learn.evidence import Delivered, EvidencePack, build_pack
from btl.learn.knowledge import Delivery
from btl.learn.questions import build_question
from btl.learn.session import Course, PreparedMatch, prepare_match

# A later question is asked at a stoppage, as most review questions are.
LATER = Delivered(Delivery.DEFERRED, 1, 2000.0, PhaseOfPlay.DEAD_BALL, "goal kick")


def packs_from(prepared: PreparedMatch, course: Course, per_concept: int) -> list[EvidencePack]:
    """A few moments of each concept in one match, at every level, asked live and later."""
    concepts = dict.fromkeys(candidate.concept for candidate in prepared.candidates)
    built: list[EvidencePack] = []
    for concept in concepts:
        moments = [c for c in prepared.candidates if c.concept == concept][:per_concept]
        for candidate in moments:
            live = Delivered(
                Delivery.LIVE, candidate.period_id, candidate.time_seconds, candidate.phase
            )
            for level in (1, 2, 3):
                for delivered in (live, LATER):
                    question = build_question(
                        candidate,
                        level,
                        delivered.delivery,
                        prepared.ctx,
                        course.threat,
                        np.random.default_rng(level),
                    )
                    if question is not None:
                        built.append(
                            build_pack(
                                question,
                                delivered,
                                prepared.ctx,
                                course.threat,
                                course.league,
                                course.concept_map,
                            )
                        )
    return built


def sample_packs(course: Course, seeds: Iterable[int], per_kind: int) -> list[EvidencePack]:
    """Up to ``per_kind`` packs for each kind of question, level and delivery, over the seeds.

    Each seed is a viewer's session seed; all three of its matches are used.
    """
    packs = [
        pack
        for seed in seeds
        for number in (1, 2, 3)
        for pack in packs_from(prepare_match(course, seed, number), course, per_concept=2)
    ]
    return balanced(packs, per_kind)


def balanced(packs: Sequence[EvidencePack], per_kind: int) -> list[EvidencePack]:
    """At most ``per_kind`` packs of each kind of question, level and delivery, in order."""
    kept: list[EvidencePack] = []
    counts: dict[tuple[str, int, str], int] = {}
    for pack in packs:
        kind = (pack.asks.value, pack.level, pack.timing.delivery)
        if counts.get(kind, 0) < per_kind:
            counts[kind] = counts.get(kind, 0) + 1
            kept.append(pack)
    return kept
