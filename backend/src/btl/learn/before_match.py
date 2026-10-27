"""What a viewer meets before a match: First looks, Level-ups, their levels, and what opened up.

Between Matches and Who's playing the page runs two short flows, both built here from the
attempt log and the record:

- **First look**, one step per active concept the viewer hasn't been introduced to (the welcome
  covers every concept active when they started; concepts that go live later get a step here).
- **Level-up**, one step per concept whose band rose over the viewer's last match, from the
  full-time report's before and after. A concept that jumped two bands gets one step.

Both end on the viewer's level in every active concept, and the Level-up flow says what the
team sheet now shows if their best concept reached a new stage.
"""

from collections.abc import Callable
from dataclasses import dataclass

from btl.learn.bkt import BktState
from btl.learn.concept_map import ConceptKey
from btl.learn.curriculum import strand_name, waits_for
from btl.learn.learner import LearnerState
from btl.learn.levels import Band, band_for, band_rose, level_word
from btl.learn.report import Break, report
from btl.learn.session import Course, PreparedMatch
from btl.learn.team_sheet import STAGE_OPENED, sheet_stage
from btl.schema.ids import TeamId


@dataclass(frozen=True, slots=True)
class LevelRow:
    """The viewer's level on one active concept, for a level list.

    ``waits_for`` names the askable prerequisites the viewer hasn't unlocked yet; ``moved``
    says whether the concept's band rose over the last match.
    """

    key: ConceptKey
    name: str
    strand: str
    strand_name: str
    mastery: float
    level: str
    band: Band
    mastered: bool
    waits_for: tuple[str, ...]
    moved: bool


@dataclass(frozen=True, slots=True)
class LevelUp:
    """A concept whose band rose over the viewer's last match: before and after."""

    key: ConceptKey
    name: str
    strand: str
    strand_name: str
    before: float
    after: float
    level_before: str
    level: str
    band_before: Band
    band: Band
    mastered: bool


@dataclass(frozen=True, slots=True)
class BeforeMatch:
    """What the page runs before the viewer's next match."""

    match_number: int
    first_looks: tuple[LevelRow, ...]
    level_ups: tuple[LevelUp, ...]
    levels: tuple[LevelRow, ...]
    unlock_note: str | None


def before_match(
    course: Course,
    state: LearnerState,
    prepare: Callable[[int, int, TeamId | None], PreparedMatch],
) -> BeforeMatch:
    """The First looks, Level-ups and levels before the match the viewer is about to watch.

    Args:
        course: What every viewer shares.
        state: The viewer's record; they mustn't have finished.
        prepare: Gives the prepared match for a session seed, match number and club, for the
            last match's report.
    """
    model = course.model
    now = state.model_state(model, course.active)
    level_ups = _level_ups(course, state, prepare)
    moved = {up.key for up in level_ups}
    levels = tuple(_row(course, now, key, key in moved) for key in course.active)
    by_key = {row.key: row for row in levels}
    return BeforeMatch(
        match_number=state.match_number,
        first_looks=tuple(by_key[key] for key in state.not_yet_introduced(course.active)),
        level_ups=level_ups,
        levels=levels,
        unlock_note=_unlock_note(course, state, now),
    )


def _level_ups(
    course: Course,
    state: LearnerState,
    prepare: Callable[[int, int, TeamId | None], PreparedMatch],
) -> tuple[LevelUp, ...]:
    last = state.match_number - 1
    if last < 1:
        return ()
    made = report(course, state, prepare(state.seed, last, state.club), last, Break.FULL_TIME)
    return tuple(
        LevelUp(
            key=move.key,
            name=move.name,
            strand=move.strand,
            strand_name=strand_name(move.strand),
            before=move.before,
            after=move.after,
            level_before=move.level_before,
            level=move.level,
            band_before=move.band_before,
            band=move.band,
            mastered=move.mastered,
        )
        for move in made.concepts
        if band_rose(move.before, move.after)
    )


def _row(course: Course, now: BktState, key: ConceptKey, moved: bool) -> LevelRow:
    model = course.model
    concept = course.concept_map.concept(key)
    mastery = model.mastery(now, key)
    return LevelRow(
        key=key,
        name=concept.name,
        strand=concept.strand,
        strand_name=strand_name(concept.strand),
        mastery=mastery,
        level=level_word(mastery, model.thresholds),
        band=band_for(mastery),
        mastered=mastery >= model.thresholds.mastery,
        waits_for=waits_for(course, now, key),
        moved=moved,
    )


def _unlock_note(course: Course, state: LearnerState, now: BktState) -> str | None:
    """What the team sheet newly shows, if the viewer's stage rose over their last match."""
    if state.match_number < 2:
        return None
    model = course.model
    earlier = tuple(a for a in state.attempts if a.match_number < state.match_number - 1)
    at_kickoff = LearnerState(state.viewer_id, state.seed, attempts=earlier).model_state(
        model, course.active
    )
    was = sheet_stage(model.mastery(at_kickoff, key) for key in course.active)
    is_now = sheet_stage(model.mastery(now, key) for key in course.active)
    return STAGE_OPENED.get(is_now) if is_now > was else None
