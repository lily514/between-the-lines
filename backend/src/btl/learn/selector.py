"""The live selector: which moments to ask about, at which level, and when.

It walks through a match in time order, the way a viewer watches it. At each candidate moment
it decides whether to ask, from the viewer's mastery *at that moment*, so an answer changes
the very next decision:

- **Which concepts:** the frontier, from the concept map and the knowledge model.
- **Which level:** from mastery (below 0.4 → level 1, below 0.7 → level 2, otherwise 3). A
  moment fits a level when its difficulty is in that level's band; the bands overlap.
- **When:** never during a transition. A moment in settled play is asked live. One in a
  transition, or after which play went on (advantage), is queued and asked, as a review, at
  the next dead ball long enough for a question, or at half-time or full time. A restart, or
  a foul that stops play, is asked live in the dead ball straight after it, however short, or
  not at all. A review never names a restart the moment itself led to.
- **How often:** at least ``SPACING`` match seconds between questions, at most
  ``IN_PLAY_CAP`` questions while the match is on, and ``BREAK_CAP`` more at each break.
  The breaks also guarantee at least ``MINIMUM_PER_MATCH`` questions: if there are fewer, a
  break asks about the best moment already passed, whatever its difficulty. Tier-0 concepts
  come round every few minutes, so each is asked at most ``TIER0_CAP`` times a match, and
  all of them ``TIER0_MATCH_CAP`` times, leaving room for the others.
- **One per stoppage:** a dead ball whose own restart or foul will be asked about live doesn't
  also ask a saved review; the review waits for the next long stoppage or a break.
- **Not near the whistle:** nothing is asked in play or at a dead ball in the last
  ``WHISTLE_MARGIN`` seconds of a half. A settled moment there is saved for the break; a
  restart or foul there isn't asked, since it is asked at its own stoppage or not at all.

When every active concept is mastered, it asks the occasional level-3 review question.
"""

import math
from collections import Counter
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum

from btl.concepts.phase import PhaseOfPlay, PhaseTimeline, Segment
from btl.learn.candidates import AskedWhen, Candidate
from btl.learn.concept_map import ConceptKey, ConceptMap, Thresholds
from btl.learn.evidence import Delivered
from btl.learn.knowledge import Delivery
from btl.learn.pace import Caps, Pace
from btl.schema.event import Event
from btl.schema.ids import ActionId
from btl.schema.scoreboard import PERIOD_MINUTES
from btl.schema.vocab import ActionType

LEVEL_FLOORS = ((0.7, 3), (0.4, 2), (0.0, 1))
BANDS: Mapping[int, tuple[float, float]] = {1: (0.0, 0.4), 2: (0.3, 0.7), 3: (0.6, 1.0)}
SPACING = 8 * 60.0
IN_PLAY_CAP = 4
BREAK_CAP = 2
MINIMUM_PER_MATCH = 2
QUEUE_LIMIT = 2
# With everything mastered, review stays occasional.
REVIEW_CAP = 1
TIER0_CAP = 2
TIER0_MATCH_CAP = 5
WHISTLE_MARGIN = 30.0
# The viewer's Preferences setting scales the caps; off asks nothing at all.
PACE_CAPS: Mapping[Pace, Caps] = {
    Pace.NORMAL: Caps(IN_PLAY_CAP, BREAK_CAP, MINIMUM_PER_MATCH),
    Pace.RARELY: Caps(1, BREAK_CAP, MINIMUM_PER_MATCH),
    Pace.OFF: Caps(0, 0, 0),
}
RESTART_NAMES: Mapping[ActionType, str] = {
    ActionType.THROW_IN: "throw-in",
    ActionType.GOALKICK: "goal kick",
    ActionType.CORNER_CROSSED: "corner",
    ActionType.CORNER_SHORT: "corner",
    ActionType.FREEKICK_CROSSED: "free kick",
    ActionType.FREEKICK_SHORT: "free kick",
    ActionType.SHOT_FREEKICK: "free kick",
    ActionType.SHOT_PENALTY: "penalty",
    ActionType.PASS: "kickoff",
}


@dataclass(frozen=True, slots=True)
class Prompt:
    """A decision to ask about a candidate, at a level, at a time."""

    candidate: Candidate
    level: int
    delivered: Delivered


def level_for(mastery: float) -> int:
    """The question level that suits a viewer's mastery of a concept."""
    return next(level for floor, level in LEVEL_FLOORS if mastery >= floor)


def fits_level(candidate: Candidate, level: int) -> bool:
    """Whether a moment's difficulty is in the band for a level."""
    low, high = BANDS[level]
    return low <= candidate.difficulty <= high


class _Kind(Enum):
    CANDIDATE = 0
    DEAD_BALL = 1
    BREAK = 2


@dataclass(slots=True)
class _Walk:
    in_play: int = 0
    asked: int = 0
    last_asked: float | None = None


def run_match(
    candidates: Sequence[Candidate],
    timeline: PhaseTimeline,
    events: Sequence[Event],
    concept_map: ConceptMap,
    active: Collection[ConceptKey],
    thresholds: Thresholds,
    mastery: Callable[[ConceptKey], float],
    ask: Callable[[Prompt], bool],
    pace: Pace = Pace.NORMAL,
) -> tuple[Prompt, ...]:
    """Walk through a match, asking about moments as they come.

    Args:
        candidates: The match's candidate moments, in match order.
        timeline: The match's phases of play.
        events: The match's events, for naming restarts.
        concept_map: For the frontier.
        active: The concepts the app can ask about.
        thresholds: The knowledge model's thresholds.
        mastery: The viewer's current mastery of a concept; read afresh at every decision.
        ask: Asks the viewer one question, and returns whether it was asked. A question
            that can't be built returns False and doesn't count.
        pace: How often the viewer wants questions; it sets the caps.

    Returns:
        Every question asked, in order.
    """
    caps = PACE_CAPS[pace]
    walk = _Walk()
    period_ends = _period_ends(timeline)
    queue: list[Candidate] = []
    passed: list[Candidate] = []
    used: set[tuple[str, int]] = set()
    asked: list[Prompt] = []
    basics: Counter[ConceptKey] = Counter()

    def deliver(prompt: Prompt, *, in_play: bool) -> bool:
        if not ask(prompt):
            return False
        used.add(_identity(prompt.candidate))
        asked.append(prompt)
        if concept_map.concept(prompt.candidate.concept).tier == 0:
            basics[prompt.candidate.concept] += 1
        walk.asked += 1
        walk.in_play += in_play
        walk.last_asked = _match_seconds(prompt.delivered.period_id, prompt.delivered.time_seconds)
        return True

    def frontier() -> tuple[ConceptKey, ...]:
        return concept_map.frontier({key: mastery(key) for key in active}, active, thresholds)

    def reviewing() -> bool:
        return not frontier()

    def capped(concept: ConceptKey) -> bool:
        if concept_map.concept(concept).tier != 0:
            return False
        return basics[concept] >= TIER0_CAP or basics.total() >= TIER0_MATCH_CAP

    def wanted(concept: ConceptKey) -> bool:
        in_reach = concept in frontier() or (reviewing() and concept in active)
        return in_reach and not capped(concept)

    def level_now(concept: ConceptKey) -> int:
        return 3 if reviewing() else level_for(mastery(concept))

    def spaced(period_id: int, seconds: float) -> bool:
        now = _match_seconds(period_id, seconds)
        return walk.last_asked is None or now - walk.last_asked >= SPACING

    def room_in_play() -> bool:
        cap = min(REVIEW_CAP, caps.in_play) if reviewing() else caps.in_play
        return walk.in_play < cap

    def near_the_whistle(period_id: int, seconds: float) -> bool:
        return seconds > period_ends.get(period_id, math.inf) - WHISTLE_MARGIN

    def asked_at(stoppage: Segment) -> bool:
        # Whether a restart or foul in this dead ball will be asked about live, as it comes.
        return any(
            c.asked_when is AskedWhen.AT_THE_STOPPAGE
            and c.period_id == stoppage.period_id
            and stoppage.start < c.time_seconds <= stoppage.end
            and wanted(c.concept)
            and fits_level(c, level_now(c.concept))
            for c in candidates
        )

    for kind, period_id, seconds, item in _walk_order(candidates, timeline):
        if kind is _Kind.CANDIDATE:
            assert isinstance(item, Candidate)
            at_the_stoppage = item.asked_when is AskedWhen.AT_THE_STOPPAGE
            if not at_the_stoppage:
                passed.append(item)
            level = level_now(item.concept)
            if not (wanted(item.concept) and fits_level(item, level)):
                continue
            late = near_the_whistle(period_id, seconds)
            if at_the_stoppage:
                if room_in_play() and spaced(period_id, seconds) and not late:
                    now = Delivered(Delivery.LIVE, period_id, seconds, PhaseOfPlay.DEAD_BALL)
                    deliver(Prompt(item, level, now), in_play=True)
                continue
            settled = item.phase is PhaseOfPlay.SETTLED and item.asked_when is AskedWhen.IN_PLAY
            if settled and not late:
                if room_in_play() and spaced(period_id, seconds):
                    live = Delivered(Delivery.LIVE, period_id, seconds, PhaseOfPlay.SETTLED)
                    deliver(Prompt(item, level, live), in_play=True)
            elif len(queue) < QUEUE_LIMIT and item.concept not in {c.concept for c in queue}:
                queue.append(item)
            continue

        assert isinstance(item, Segment)
        if kind is _Kind.DEAD_BALL:
            if not (room_in_play() and spaced(period_id, seconds)):
                continue
            if near_the_whistle(period_id, seconds) or asked_at(item):
                continue
            restart = RESTART_NAMES.get(events[item.last].action_type)
            when = Delivered(Delivery.DEFERRED, period_id, seconds, PhaseOfPlay.DEAD_BALL, restart)
            _deliver_queued(
                queue, when, wanted, level_now, deliver, limit=1, in_play=True, stopped=item.first
            )
            continue

        when = Delivered(Delivery.DEFERRED, period_id, seconds, item.phase)
        delivered = _deliver_queued(
            queue, when, wanted, level_now, deliver, limit=caps.per_break, in_play=False
        )
        while delivered < caps.per_break and walk.asked < caps.minimum:
            best = _best_passed(passed, used, wanted, level_now)
            if best is None or not deliver(
                Prompt(best, level_now(best.concept), when), in_play=False
            ):
                break
            delivered += 1
    return tuple(asked)


def _deliver_queued(
    queue: list[Candidate],
    when: Delivered,
    wanted: Callable[[ConceptKey], bool],
    level_now: Callable[[ConceptKey], int],
    deliver: Callable[..., bool],
    *,
    limit: int,
    in_play: bool,
    stopped: ActionId | None = None,
) -> int:
    """Ask about the oldest queued moments still worth asking, re-levelled to mastery now.

    ``stopped`` is the action after which play stopped, at a dead ball. A moment that includes
    it led to the restart, such as an offside free kick, so naming the restart would hint.
    """
    delivered = 0
    while queue and delivered < limit:
        candidate = queue.pop(0)
        if not wanted(candidate.concept):
            continue
        first, last = candidate.tag.span
        led_to_it = stopped is not None and first <= stopped <= last
        asked_when = replace(when, restart=None) if led_to_it else when
        prompt = Prompt(candidate, level_now(candidate.concept), asked_when)
        if deliver(prompt, in_play=in_play):
            delivered += 1
    return delivered


def _best_passed(
    passed: Sequence[Candidate],
    used: set[tuple[str, int]],
    wanted: Callable[[ConceptKey], bool],
    level_now: Callable[[ConceptKey], int],
) -> Candidate | None:
    """The unasked moment so far whose difficulty is nearest the middle of its level's band."""

    def distance(candidate: Candidate) -> float:
        low, high = BANDS[level_now(candidate.concept)]
        return abs(candidate.difficulty - (low + high) / 2)

    unasked = [c for c in passed if _identity(c) not in used and wanted(c.concept)]
    return min(unasked, key=distance, default=None)


def _walk_order(
    candidates: Sequence[Candidate], timeline: PhaseTimeline
) -> Iterator[tuple[_Kind, int, float, Candidate | Segment]]:
    """Candidates, long-enough dead balls and breaks, in the order a viewer meets them."""
    items: list[tuple[tuple[int, float, int], _Kind, Candidate | Segment]] = []
    for candidate in candidates:
        key = (candidate.period_id, candidate.time_seconds, _Kind.CANDIDATE.value)
        items.append((key, _Kind.CANDIDATE, candidate))
    for segment in timeline.segments:
        if not segment.long_enough_to_ask:
            continue
        kind = _Kind.DEAD_BALL if segment.phase is PhaseOfPlay.DEAD_BALL else _Kind.BREAK
        items.append(((segment.period_id, segment.start, kind.value), kind, segment))
    for (period_id, seconds, _), kind, item in sorted(items, key=lambda entry: entry[0]):
        yield kind, period_id, seconds, item


def _period_ends(timeline: PhaseTimeline) -> dict[int, float]:
    # A period ends where its break, half-time or full time, begins.
    breaks = (PhaseOfPlay.HALF_TIME, PhaseOfPlay.FULL_TIME)
    return {s.period_id: s.start for s in timeline.segments if s.phase in breaks}


def _identity(candidate: Candidate) -> tuple[str, int]:
    return candidate.tag.concept.value, candidate.tag.action_id


def _match_seconds(period_id: int, seconds: float) -> float:
    return (period_id - 1) * PERIOD_MINUTES * 60 + seconds
