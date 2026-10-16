"""Every detector, listed explicitly so none can be left out by a forgotten import."""

from collections.abc import Sequence

from btl.concepts.base import ConceptTag, Detector, MatchContext
from btl.concepts.counter_attack import CounterAttack
from btl.concepts.counter_press import CounterPress
from btl.concepts.line_breaking import LineBreakingPass
from btl.concepts.restart import BallOutOfPlay
from btl.concepts.switch_of_play import SwitchOfPlay

ALL_DETECTORS: tuple[Detector, ...] = (
    SwitchOfPlay(),
    LineBreakingPass(),
    CounterPress(),
    CounterAttack(),
    BallOutOfPlay(),
)


def detect_all(
    ctx: MatchContext, detectors: Sequence[Detector] = ALL_DETECTORS
) -> tuple[ConceptTag, ...]:
    """Run detectors over a match, skipping those that need snapshots when it has none.

    Returns:
        Every tag, ordered by key action, then concept.
    """
    tags = [
        tag
        for detector in detectors
        if ctx.has_snapshots or not detector.needs_snapshots
        for tag in detector.detect(ctx)
    ]
    return tuple(sorted(tags, key=lambda tag: (tag.action_id, tag.concept)))
