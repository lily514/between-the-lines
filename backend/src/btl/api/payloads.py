"""Turning the learning loop's objects into the API's shapes.

A question payload is built from the question view and the selector's timing only, never from
the pack, so the right answer and the outcome facts can't reach the browser before the viewer
answers. The feedback payload is the whole pack.
"""

from collections.abc import Mapping
from typing import Literal

from btl.api.models import (
    Bar,
    ClubOut,
    DeliveredTime,
    FactOut,
    FeedbackOption,
    FeedbackOut,
    MarkerOut,
    MatchOut,
    MomentTime,
    Movement,
    OptionOut,
    PictureOut,
    PlayerNumbersOut,
    PositionOut,
    QuestionOut,
    ScoreOut,
    SheetPlayerOut,
    SheetTeamOut,
    TeamSheetOut,
    ThresholdsOut,
    YourTeam,
)
from btl.concepts.phase import PhaseOfPlay
from btl.league.league import Club, League
from btl.learn.concept_map import Thresholds
from btl.learn.evidence import Fact, Picture, percent_points
from btl.learn.knowledge import Delivery
from btl.learn.matches import MatchState, ViewerMatch
from btl.learn.questions import Form
from btl.learn.session import Asked, Told
from btl.learn.team_sheet import NEXT_STAGE, SheetPlayer, SheetTeam, TeamSheet
from btl.schema.ids import TeamId
from btl.schema.scoreboard import clock


def question_payload(
    asked: Asked, match_number: int, home: Club, away: Club, club: TeamId | None
) -> QuestionOut:
    """The question as the page shows it: its view, its wording and when it is asked."""
    view, prompt = asked.view, asked.prompt
    candidate, delivered = prompt.candidate, prompt.delivered
    return QuestionOut(
        pack_id=view.pack_id,
        match_number=match_number,
        home=home.name,
        away=away.name,
        home_code=home.short_name,
        away_code=away.short_name,
        your_team=your_team(club, home, away),
        concept_name=view.concept_name,
        form="predict" if view.form is Form.PREDICT else "identify",
        asks=view.asks.value,
        level=view.level,
        text=asked.text,
        occurred=_moment(candidate.period_id, candidate.time_seconds, candidate.phase),
        delivered=DeliveredTime(
            **_moment(delivered.period_id, delivered.time_seconds, delivered.phase).model_dump(),
            delivery="live" if delivered.delivery is Delivery.LIVE else "deferred",
            restart=delivered.restart,
        ),
        context=_facts(view.context),
        options=[
            OptionOut(
                key=option.key,
                label=option.label,
                neutral=_facts(option.neutral),
                target_at=option.target_at,
            )
            for option in view.options
        ],
        picture=_picture(view.picture),
    )


def feedback_payload(
    told: Told,
    before: Mapping[str, float],
    thresholds: Thresholds,
    match_number: int,
    match_seed: int,
) -> FeedbackOut:
    """The feedback with the whole evidence pack, and how each concept's mastery moved."""
    pack, grade = told.pack, told.grade
    return FeedbackOut(
        pack_id=pack.pack_id,
        correct=grade.correct,
        chosen=grade.chosen,
        correct_key=pack.correct_key,
        verdict=told.verdict,
        explanation=told.explanation,
        takeaway=told.takeaway,
        misconception=told.misconception,
        source=told.source,
        update=told.update,
        concept_name=pack.concept.name,
        level=pack.level,
        match_number=match_number,
        action_id=pack.picture.action_id,
        match_seed=match_seed,
        context=_facts(pack.context),
        outcome=_facts(pack.outcome),
        options=[
            FeedbackOption(
                key=option.key,
                label=option.label,
                correct=option.correct,
                chosen=option.key == grade.chosen,
                neutral=_facts(option.neutral),
                outcome=_facts(option.outcome),
                target_at=option.target_at,
            )
            for option in pack.options
        ],
        picture=_picture(pack.picture),
        reveal_path=list(pack.reveal_path),
        reveal_line=pack.reveal_line,
        concepts=movements(before, told.mastery),
        thresholds=thresholds_payload(thresholds),
    )


def your_team(club: TeamId | None, home: Club, away: Club) -> YourTeam:
    """Which side the viewer's team is in a match, if either."""
    if club == home.team_id:
        return "home"
    if club == away.team_id:
        return "away"
    return None


def your_result(
    side: YourTeam, home_goals: int, away_goals: int
) -> Literal["won", "drew", "lost"] | None:
    """The result for the viewer's team, if it played."""
    if side is None:
        return None
    ours, theirs = (home_goals, away_goals) if side == "home" else (away_goals, home_goals)
    return "won" if ours > theirs else "drew" if ours == theirs else "lost"


def club_payload(club: Club) -> ClubOut:
    """A club by id, name and code."""
    return ClubOut(team_id=club.team_id, name=club.name, code=club.short_name)


def team_sheet_payload(sheet: TeamSheet) -> TeamSheetOut:
    """The team sheet, with kick-off spots to the tenth of a metre."""
    return TeamSheetOut(
        match_number=sheet.match_number,
        stage=sheet.stage,
        next_stage=NEXT_STAGE.get(sheet.stage),
        teams=[_sheet_team(team) for team in sheet.teams],
    )


def _sheet_team(team: SheetTeam) -> SheetTeamOut:
    return SheetTeamOut(
        team_id=team.team_id,
        name=team.name,
        code=team.short_name,
        home=team.home,
        yours=team.yours,
        formation=team.formation,
        matches_watched=team.matches_watched,
        players=[_sheet_player(player) for player in team.players],
    )


def _sheet_player(player: SheetPlayer) -> SheetPlayerOut:
    spot = player.at_kickoff
    numbers = player.numbers
    return SheetPlayerOut(
        shirt=player.shirt_number,
        name=player.name,
        role=player.role.value,
        position=PositionOut(
            short=player.position.short,
            name=player.position.name,
            description=player.position.description,
        ),
        at_kickoff=None if spot is None else (round(spot[0], 1), round(spot[1], 1)),
        numbers=None
        if numbers is None
        else PlayerNumbersOut(
            matches=numbers.matches,
            passes_completed=numbers.passes_completed,
            passes_tried=numbers.passes_tried,
            line_breaking_passes=numbers.line_breaking_passes,
            threat_added=_fact(percent_points(numbers.threat_added)),
        ),
    )


def match_payload(match: ViewerMatch, league: League, club: TeamId | None) -> MatchOut:
    """One of the viewer's matches, with the result from their side once it is finished."""
    home, away = league.club(match.home_id), league.club(match.away_id)
    side = your_team(club, home, away)
    score = match.score
    finished = match.state is MatchState.FINISHED
    score_out = None
    if score is not None:
        score_out = ScoreOut(home=score.home, away=score.away, clock=score.clock)
    return MatchOut(
        match_number=match.match_number,
        matchday=match.matchday.number,
        date=match.matchday.day.isoformat(),
        date_label=match.matchday.label,
        kick_off=match.matchday.kick_off,
        home=home.name,
        away=away.name,
        home_code=home.short_name,
        away_code=away.short_name,
        your_team=side,
        state=match.state.value,
        score=score_out,
        your_result=your_result(side, score.home, score.away) if finished and score else None,
        questions=match.questions,
    )


def movements(before: Mapping[str, float], after: Mapping[str, float]) -> list[Movement]:
    """Each concept's mastery before and after, in the order of ``after``."""
    return [Movement(name=name, before=before[name], after=value) for name, value in after.items()]


def bars(mastery: Mapping[str, float]) -> list[Bar]:
    """Each concept's mastery now."""
    return [Bar(name=name, value=value) for name, value in mastery.items()]


def thresholds_payload(thresholds: Thresholds) -> ThresholdsOut:
    """The knowledge model's thresholds, for the ticks on a progress bar."""
    return ThresholdsOut(unlock=thresholds.unlock, mastery=thresholds.mastery)


def _moment(period_id: int, time_seconds: float, phase: PhaseOfPlay) -> MomentTime:
    return MomentTime(
        period=period_id,
        seconds=time_seconds,
        clock=clock(period_id, time_seconds),
        phase=phase.value,
    )


def _facts(facts: Mapping[str, Fact]) -> dict[str, FactOut]:
    return {name: _fact(fact) for name, fact in facts.items()}


def _fact(fact: Fact) -> FactOut:
    return FactOut(value=fact.value, display=fact.display)


def _picture(picture: Picture) -> PictureOut:
    return PictureOut(
        action_id=picture.action_id,
        markers=[
            MarkerOut(
                shirt=m.shirt,
                side="attacking" if m.side == "attacking" else "defending",
                home=m.home,
                x=m.x,
                y=m.y,
                role=m.role,
            )
            for m in picture.markers
        ],
        ball=picture.ball,
        path=list(picture.path),
        mark=picture.mark,
    )
