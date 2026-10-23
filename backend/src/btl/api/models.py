"""The shapes the web API sends and receives, as pydantic models.

They mirror the learning loop's own types (`QuestionView`, `Told`) closely, so the page's
generated TypeScript types read like the engine's. A question carries only what its view
holds; the right answer and every outcome arrive with the feedback.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

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


class QuestionOut(BaseModel):
    """The next question, built from its question view only."""

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


class Bar(BaseModel):
    """One concept's mastery, from 0 to 1."""

    name: str
    value: float


class Movement(BaseModel):
    """How one concept's mastery moved: before and after, from 0 to 1."""

    name: str
    before: float
    after: float


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


class StartIn(BaseModel):
    """Start watching, or carry on. Without a seed, the viewer's name chooses their matches.

    A ``club`` (team id) makes the viewer's matches that club's fixtures, if they haven't
    started watching.
    """

    viewer_id: str
    seed: int | None = None
    club: int | None = None


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
    seen them play.
    """

    shirt: int
    name: str
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


class AnswerIn(BaseModel):
    """An answer to the pending question, which ``pack_id`` names."""

    pack_id: str
    key: str
