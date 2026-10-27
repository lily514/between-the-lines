from collections import Counter
from dataclasses import dataclass, field

from btl.concepts.base import ConceptTag, MatchContext, match_context
from btl.concepts.registry import ALL_DETECTORS, detect_all
from btl.schema.ids import ActionId
from btl.schema.vocab import ConceptId
from tests.fixtures.concepts import switches_match
from tests.fixtures.matches import six_event_match


@dataclass(frozen=True, slots=True)
class TagsEveryEvent:
    """A stand-in detector that tags every event, optionally needing snapshots."""

    needs_snapshots: bool
    concept: ConceptId = field(default=ConceptId.SWITCH_OF_PLAY, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        return tuple(
            ConceptTag(
                self.concept,
                event.game_id,
                event.action_id,
                (event.action_id, event.action_id),
                None,
                {},
            )
            for event in reversed(ctx.events)
        )


def test_every_concept_has_exactly_one_detector() -> None:
    detectors_per_concept = Counter(detector.concept for detector in ALL_DETECTORS)

    assert detectors_per_concept == Counter(set(ConceptId))


def test_detectors_that_need_snapshots_are_skipped_when_there_are_none() -> None:
    no_snapshots = match_context(switches_match())

    tags = detect_all(no_snapshots, [TagsEveryEvent(needs_snapshots=True)])

    assert tags == ()


def test_detectors_that_need_snapshots_run_when_there_are_some() -> None:
    with_snapshots = match_context(six_event_match())

    tags = detect_all(with_snapshots, [TagsEveryEvent(needs_snapshots=True)])

    assert len(tags) == len(six_event_match().events)


def test_tags_come_back_in_event_order() -> None:
    tags = detect_all(match_context(switches_match()), [TagsEveryEvent(needs_snapshots=False)])

    assert [tag.action_id for tag in tags] == [ActionId(i) for i in range(7)]


def test_all_detectors_find_the_switches_and_the_ball_win_in_the_fixture() -> None:
    tags = detect_all(match_context(switches_match()))

    assert [(tag.concept, tag.action_id) for tag in tags] == [
        (ConceptId.SWITCH_OF_PLAY, 0),
        (ConceptId.BALL_WIN, 5),
        (ConceptId.SWITCH_OF_PLAY, 6),
    ]
