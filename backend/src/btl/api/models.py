"""The shapes the web API sends and receives, as pydantic models.

They mirror the learning loop's own types (`QuestionView`, `Told`) closely, so the page's
generated TypeScript types read like the engine's. A question carries only what its view
holds; the right answer and every outcome arrive with the feedback.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from btl.learn.levels import Band
from btl.learn.pace import Pace

Point = tuple[float, float]
# Which side of a match is the viewer's team, if either.
YourTeam = Literal["home", "away"] | None


class FactOut(BaseModel):
    """A fact: its value, and the text to show for it (number only, as the engine formats it)."""

    value: float | str
    display: str


class MarkerOut(BaseModel):
    """A player on the picture, with the team on the ball attacking left to right."""

    shirt: int
    side: Literal["attacking", "defending"]
    home: bool
    x: float
    y: float
    role: str


class PictureOut(BaseModel):
    """The players and the ball at the moment, and the play's path when the form shows it.

    ``mark`` is a spot the question is about, such as where the ball went out for a throw-in.
    """

    action_id: int
    markers: list[MarkerOut]
    ball: Point
    path: list[Point]
    mark: Point | None


class MomentTime(BaseModel):
    """A point in the match: period, seconds into it, the match clock and the phase of play."""

    period: int
    seconds: float
    clock: str
    phase: str


class DeliveredTime(MomentTime):
    """When a question is asked: live, or deferred to a stoppage or break (``restart`` names it)."""

    delivery: Literal["live", "deferred"]
    restart: str | None


class OptionOut(BaseModel):
    """An answer option as a question shows it. ``target_at`` is where a pass would go."""

    key: str
    label: str
    neutral: dict[str, FactOut]
    target_at: Point | None


class ScoreOut(BaseModel):
    """Goals for each side, at ``clock`` for a match in progress (null at full time)."""

    home: int
    away: int
    clock: str | None


class TouchOut(BaseModel):
    """A player on the ball, at ``at`` seconds on the match clock.

    ``surname`` is what the commentary calls them by; a surname may have more than one word.
    """

    at: float
    player: str
    surname: str
    number: int


class SpellOut(BaseModel):
    """One side's spell on the ball, as the play-by-play covers it."""

    side: Literal["home", "away"]
    touches: list[TouchOut]


class PlayByPlayOut(BaseModel):
    """Who had the ball between the viewer's last question and the next, for the page to play.

    Times are seconds on the match clock: ``start`` where the viewer left off (0 at kick-off),
    ``end`` when the next question is asked. The spells stop at ``names_until``, the moment the
    question is about, so they say nothing of how that play turned out; a question saved for a
    stoppage has play between it and ``end`` that goes unnamed.
    """

    start: float
    end: float
    names_until: float
    spells: list[SpellOut]


class QuestionOut(BaseModel):
    """The next question, built from its question view only.

    ``score`` is the score as the question comes. ``catch_up`` says what happened since the
    viewer's last answer in this match, such as "Truro Otters scored at 41:02.", then the
    score; null for the match's first question.
    """

    kind: Literal["question"] = "question"
    pack_id: str
    match_number: int
    home: str
    away: str
    home_code: str
    away_code: str
    your_team: YourTeam
    concept_name: str
    form: Literal["identify", "predict"]
    asks: str
    level: int
    text: str
    occurred: MomentTime
    delivered: DeliveredTime
    context: dict[str, FactOut]
    options: list[OptionOut]
    picture: PictureOut
    score: ScoreOut
    catch_up: str | None
    play_by_play: PlayByPlayOut


class Bar(BaseModel):
    """One concept's mastery, from 0 to 1, with the level word ("Solid") and band for it.

    The band is the level as a key the page switches on; "Mastered" is the Sharp band.
    """

    key: str
    name: str
    value: float
    level: str
    band: Band
    # The askable prerequisites it still waits for; the page shows it locked while any remain.
    waits_for: list[str]


class Movement(BaseModel):
    """How one concept's mastery moved: before and after, from 0 to 1, and its level now."""

    name: str
    before: float
    after: float
    level: str
    band: Band
    mastered: bool


class ThresholdsOut(BaseModel):
    """When a concept unlocks the ones that need it, and when it counts as mastered."""

    unlock: float
    mastery: float


class Fixture(BaseModel):
    """The two clubs of a match, by name and three-letter code."""

    home: str
    away: str
    home_code: str
    away_code: str
    your_team: YourTeam


class ClubOut(BaseModel):
    """A club. The page keys its crest and colours by ``code``."""

    team_id: int
    name: str
    code: str


class FullTimeOut(BaseModel):
    """The match just finished: the score, how many questions, and how each concept moved.

    ``your_result`` is the result for the viewer's team, if it played.
    """

    kind: Literal["full_time"] = "full_time"
    match_number: int
    home: str
    away: str
    home_code: str
    away_code: str
    your_team: YourTeam
    home_goals: int
    away_goals: int
    your_result: Literal["won", "drew", "lost"] | None
    questions: int
    concepts: list[Movement]
    thresholds: ThresholdsOut
    finished: bool
    next_match: int | None


NextOut = Annotated[QuestionOut | FullTimeOut, Field(discriminator="kind")]


class FeedbackOption(BaseModel):
    """An option after answering: whether it was right or picked, and every fact about it."""

    key: str
    label: str
    correct: bool
    chosen: bool
    neutral: dict[str, FactOut]
    outcome: dict[str, FactOut]
    target_at: Point | None


class FeedbackOut(BaseModel):
    """What the viewer is told after answering, with the whole evidence behind it."""

    pack_id: str
    correct: bool
    chosen: str | None
    correct_key: str
    verdict: str
    explanation: str
    takeaway: str
    misconception: str | None
    source: str
    update: str
    concept_name: str
    level: int
    match_number: int
    action_id: int
    match_seed: int
    context: dict[str, FactOut]
    outcome: dict[str, FactOut]
    options: list[FeedbackOption]
    picture: PictureOut
    reveal_path: list[Point]
    # The offside line's x for an offside question, with the passing team attacking left to right.
    reveal_line: float | None
    concepts: list[Movement]
    thresholds: ThresholdsOut


class StatusOut(BaseModel):
    """Where a viewer stands: which match is next, and their mastery of each concept.

    ``club`` is the team they support. They can choose or change it while
    ``can_choose_club``; ``suggested_club`` is the one "Pick one for me" starts from.
    ``pace`` is how often questions come; ``pace_next`` is a change waiting for the next match.
    """

    viewer_id: str
    match_number: int
    matches: int
    finished: bool
    fixture: Fixture | None
    club: ClubOut | None
    can_choose_club: bool
    suggested_club: int
    concepts: list[Bar]
    thresholds: ThresholdsOut
    pace: Pace
    pace_next: Pace | None


class StartIn(BaseModel):
    """Start watching, or carry on. Without a seed, the viewer's name chooses their matches.

    A ``club`` (team id) makes the viewer's matches that club's fixtures, if they haven't
    started watching.
    """

    viewer_id: str
    seed: int | None = None
    club: int | None = None


class PaceIn(BaseModel):
    """How often questions should come."""

    pace: Pace


class ClubIn(BaseModel):
    """Choose the team to support, by team id."""

    club: int


class PositionOut(BaseModel):
    """A position: its abbreviation, its name and what the player there does."""

    short: str
    name: str
    description: str


class PlayerNumbersOut(BaseModel):
    """A player's numbers from the watched matches they started."""

    matches: int
    passes_completed: int
    passes_tried: int
    line_breaking_passes: int
    threat_added: FactOut


class SheetPlayerOut(BaseModel):
    """A starter on the team sheet.

    ``at_kickoff`` is where they stood at kick-off, with the sheet's first team attacking left
    to right. ``numbers`` is null before stage 3, or if the viewer hasn't
    seen them play. ``surname`` is the name on their shirt; it may have more than one word.
    """

    shirt: int
    name: str
    surname: str
    role: str
    position: PositionOut
    at_kickoff: Point
    numbers: PlayerNumbersOut | None


class SheetTeamOut(BaseModel):
    """One side: goalkeeper, defenders, midfielders, forwards, each line left to right.

    ``formation`` is null before stage 2; ``matches_watched`` is null before stage 3.
    """

    team_id: int
    name: str
    code: str
    home: bool
    yours: bool
    formation: str | None
    matches_watched: int | None
    players: list[SheetPlayerOut]


class TeamSheetOut(BaseModel):
    """Who's playing in the viewer's next match: their team first, or the home team.

    ``next_stage`` says what opens more of the sheet; null at the last stage.
    """

    match_number: int
    stage: int
    next_stage: str | None
    teams: list[SheetTeamOut]


class MatchOut(BaseModel):
    """One of the viewer's matches, for the Matches screen.

    ``score`` and ``your_result`` are null until the viewer has seen some of the match:
    an upcoming match tells only its clubs and date.
    """

    match_number: int
    matchday: int
    date: str
    date_label: str
    kick_off: str
    home: str
    away: str
    home_code: str
    away_code: str
    your_team: YourTeam
    state: Literal["upcoming", "in_progress", "finished"]
    score: ScoreOut | None
    your_result: Literal["won", "drew", "lost"] | None
    questions: int


class StrandOut(BaseModel):
    """A strand of the curriculum."""

    key: str
    name: str
    description: str


class MapConceptOut(BaseModel):
    """A concept on the map. ``mastery``, ``level`` and ``band`` are null for one coming later.

    ``waits_for`` names the askable prerequisites the viewer hasn't unlocked yet: the concept
    is locked while it isn't empty.
    """

    key: str
    name: str
    strand: str
    tier: int
    objective: str
    prerequisites: list[str]
    askable: bool
    mastery: float | None
    level: str | None
    band: Band | None
    waits_for: list[str]


class ConceptMapOut(BaseModel):
    """The whole curriculum, with the viewer's level on each concept asked about now.

    ``tiers`` names the tiers in order, from tier 0.
    """

    strands: list[StrandOut]
    tiers: list[str]
    concepts: list[MapConceptOut]
    thresholds: ThresholdsOut


class StrandValueOut(BaseModel):
    """A strand on the radar. ``kickoff`` and ``now`` are null when nothing in it is asked yet."""

    key: str
    name: str
    concepts: int
    kickoff: float | None
    now: float | None


class ConceptMoveOut(BaseModel):
    """A concept asked about now: mastery, level word and band at kick-off and at the break."""

    key: str
    name: str
    strand: str
    before: float
    after: float
    level_before: str
    level: str
    band_before: Band
    band: Band
    mastered: bool
    waits_for: list[str]


class GoalOut(BaseModel):
    """A goal, by match clock, side and scorer."""

    clock: str
    side: Literal["home", "away"]
    scorer: str
    own_goal: bool


class AnswerLineOut(BaseModel):
    """A question answered before the break: the moment's clock, the concept, right or not."""

    clock: str
    concept: str
    correct: bool


class ReportOut(BaseModel):
    """The scouting report for one of the viewer's matches at halftime or full time.

    It covers the match up to that break only. ``right`` counts the answers that were right.
    """

    match_number: int
    at: Literal["halftime", "full_time"]
    home: str
    away: str
    home_code: str
    away_code: str
    your_team: YourTeam
    home_goals: int
    away_goals: int
    your_result: Literal["won", "drew", "lost"] | None
    goals: list[GoalOut]
    strands: list[StrandValueOut]
    concepts: list[ConceptMoveOut]
    answers: list[AnswerLineOut]
    right: int
    note: str
    thresholds: ThresholdsOut


class LevelRowOut(BaseModel):
    """The viewer's level on one active concept, for a level list.

    ``waits_for`` names the askable prerequisites not yet unlocked (locked while not empty);
    ``moved`` says whether the band rose over the last match.
    """

    key: str
    name: str
    strand: str
    strand_name: str
    mastery: float
    level: str
    band: Band
    mastered: bool
    waits_for: list[str]
    moved: bool


class LevelUpOut(BaseModel):
    """A concept whose band rose over the viewer's last match: before and after."""

    key: str
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


class BeforeMatchOut(BaseModel):
    """What the page runs before the viewer's next match: First looks, then Level-ups.

    ``first_looks`` are the active concepts the viewer hasn't been introduced to; ``level_ups``
    the concepts whose band rose over their last match; ``levels`` a row per active concept;
    ``unlock_note`` what the team sheet newly shows, if their stage rose, else null.
    """

    match_number: int
    first_looks: list[LevelRowOut]
    level_ups: list[LevelUpOut]
    levels: list[LevelRowOut]
    unlock_note: str | None


class IntroducedIn(BaseModel):
    """The concepts the viewer has now had a First look at, by key."""

    concepts: list[str]


class AnswerIn(BaseModel):
    """An answer to the pending question, which ``pack_id`` names."""

    pack_id: str
    key: str
