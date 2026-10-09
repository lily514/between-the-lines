"""The shapes the web API sends and receives, as pydantic models.

They mirror the learning loop's own types (`QuestionView`, `Told`) closely, so the page's
generated TypeScript types read like the engine's. A question carries only what its view
holds; the right answer and every outcome arrive with the feedback.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Point = tuple[float, float]


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
    """The players and the ball at the moment, and the play's path when the form shows it."""

    action_id: int
    markers: list[MarkerOut]
    ball: Point
    path: list[Point]


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
    """The two clubs of a match."""

    home: str
    away: str


class FullTimeOut(BaseModel):
    """The match just finished: the score, how many questions, and how each concept moved."""

    kind: Literal["full_time"] = "full_time"
    match_number: int
    home: str
    away: str
    home_goals: int
    away_goals: int
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
    concepts: list[Movement]
    thresholds: ThresholdsOut


class StatusOut(BaseModel):
    """Where a viewer stands: which match is next, and their mastery of each concept."""

    viewer_id: str
    match_number: int
    matches: int
    finished: bool
    fixture: Fixture | None
    concepts: list[Bar]
    thresholds: ThresholdsOut


class StartIn(BaseModel):
    """Start watching, or carry on. Without a seed, the viewer's name chooses their matches."""

    viewer_id: str
    seed: int | None = None


class AnswerIn(BaseModel):
    """An answer to the pending question, which ``pack_id`` names."""

    pack_id: str
    key: str
