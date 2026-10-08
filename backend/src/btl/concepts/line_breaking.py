"""Line-breaking pass: a pass that goes through a line of defenders instead of around it."""

import math
from dataclasses import dataclass, field
from itertools import pairwise

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema.event import Event
from btl.schema.ids import TeamId
from btl.schema.snapshot import PlayerPosition, Snapshot
from btl.schema.vocab import ActionType, ConceptId, Result

LINE_SPLIT = 5.0
MIN_LINE_PLAYERS = 3
WIDE_GAP = 20.0
NARROW_GAP = 6.0
EXTRA_LINE_DIFFICULTY = 0.2


@dataclass(frozen=True, slots=True)
class _Line:
    """Defenders standing roughly level with each other, ordered across the pitch."""

    players: tuple[PlayerPosition, ...]

    @property
    def front(self) -> float:
        return min(player.x for player in self.players)

    @property
    def back(self) -> float:
        return max(player.x for player in self.players)


@dataclass(frozen=True, slots=True)
class LineBreakingPass:
    """Finds passes that break the opposition's lines.

    Out of possession, a team's outfield players stand in rough lines across the pitch: a
    back line of defenders, a midfield line, sometimes a front line. A pass that goes *through*
    a line, between two of its players, takes those players out of the game at once.

    Lines come from the snapshot at the start of the pass. The defending team's outfield
    players, sorted by how far up the pitch they stand, form a new line wherever the next player
    is more than ``line_split`` metres further on. Only lines of at least ``min_line_players``
    count; two forwards are not a line.

    A successful pass breaks a line when it starts in front of every player in the line, ends
    behind every one of them, and crosses the line between two of its players. The gap is the
    distance between those two players.

    Difficulty is how hard the pass is to see: 0 for a gap of ``wide_gap`` metres or more, rising
    to 1 at ``narrow_gap`` metres or less, judged at the narrowest gap the pass goes through.
    Each line broken after the first adds ``extra_line_difficulty``, up to 1.
    """

    line_split: float = LINE_SPLIT
    min_line_players: int = MIN_LINE_PLAYERS
    wide_gap: float = WIDE_GAP
    narrow_gap: float = NARROW_GAP
    extra_line_difficulty: float = EXTRA_LINE_DIFFICULTY
    concept: ConceptId = field(default=ConceptId.LINE_BREAKING_PASS, init=False)
    needs_snapshots: bool = field(default=True, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every line-breaking pass in the match, in event order."""
        tags: list[ConceptTag] = []
        for event in ctx.events:
            if event.action_type is not ActionType.PASS or event.result is not Result.SUCCESS:
                continue
            snapshot = ctx.snapshot(event.action_id)
            if snapshot is None:
                continue
            gaps = self.lines_broken(
                snapshot, event.team_id, (event.start_x, event.start_y), (event.end_x, event.end_y)
            )
            if gaps:
                tags.append(self._tag(event, gaps))
        return tuple(tags)

    def lines_broken(
        self,
        snapshot: Snapshot,
        team_id: TeamId,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> tuple[float, ...]:
        """The lines a pass from ``start`` to ``end`` would break, by this detector's rule.

        The pass need not have happened, so answer options can be measured the same way as the
        pass that was played. Coordinates are in the direction of ``team_id``, the passing team,
        as in `btl.concepts.base.MatchContext`.

        Returns:
            The width of the gap the pass goes through in each line it breaks, nearest line
            first. Empty if it breaks none.
        """
        return tuple(
            gap
            for line in self._lines(snapshot, team_id)
            if (gap := _gap_crossed(line, start, end)) is not None
        )

    def _lines(self, snapshot: Snapshot, team_id: TeamId) -> list[_Line]:
        defenders = sorted(
            (
                player
                for player in snapshot.positions
                if player.team_id != team_id and not player.is_goalkeeper
            ),
            key=lambda player: player.x,
        )
        groups: list[list[PlayerPosition]] = []
        for player in defenders:
            if groups and player.x - groups[-1][-1].x <= self.line_split:
                groups[-1].append(player)
            else:
                groups.append([player])
        return [
            _Line(tuple(sorted(group, key=lambda player: player.y)))
            for group in groups
            if len(group) >= self.min_line_players
        ]

    def _tag(self, event: Event, gaps: tuple[float, ...]) -> ConceptTag:
        narrowest = min(gaps)
        openness = (narrowest - self.narrow_gap) / (self.wide_gap - self.narrow_gap)
        difficulty = 1 - min(max(openness, 0.0), 1.0)
        difficulty = min(1.0, difficulty + self.extra_line_difficulty * (len(gaps) - 1))
        return ConceptTag(
            concept=self.concept,
            game_id=event.game_id,
            action_id=event.action_id,
            span=(event.action_id, event.action_id),
            difficulty=round(difficulty, 2),
            evidence={"lines broken": len(gaps), "gap (m)": round(narrowest, 1)},
        )


def _gap_crossed(line: _Line, start: tuple[float, float], end: tuple[float, float]) -> float | None:
    """The width of the gap the pass goes through, or None if it doesn't go through the line."""
    (start_x, start_y), (end_x, end_y) = start, end
    if not (start_x < line.front and end_x > line.back):
        return None
    line_x = (line.front + line.back) / 2
    along = (line_x - start_x) / (end_x - start_x)
    crossing_y = start_y + along * (end_y - start_y)
    for left, right in pairwise(line.players):
        if left.y <= crossing_y <= right.y:
            return math.hypot(right.x - left.x, right.y - left.y)
    return None
