"""Planted moments: the teachable moments a match was built to contain, and where they are."""

from dataclasses import dataclass

from btl.schema.ids import ActionId
from btl.schema.vocab import ConceptId


@dataclass(frozen=True, slots=True)
class PlantedMoment:
    """A teachable moment written into a match on purpose: the key to a future question.

    Play pauses once ``pause_action_id`` ends, and the learner sees the snapshot at the start
    of the next action. ``answer_action_id`` is the action the question is about: that next
    action itself, or one a little later. ``difficulty`` is the level that was asked for, from
    1 (easiest) up.
    """

    concept: ConceptId
    difficulty: int
    pause_action_id: ActionId
    answer_action_id: ActionId
