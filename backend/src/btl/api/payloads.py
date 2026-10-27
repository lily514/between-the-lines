"""Turning the learning loop's objects into the API's shapes.

A question payload is built from the question view and the selector's timing only, never from
the pack, so the right answer and the outcome facts can't reach the browser before the viewer
answers. Its play-by-play comes from the match, and stops before the moment asked about. The
feedback payload is the whole pack.
"""

from collections.abc import Mapping
from typing import Literal

from btl.api.models import (
    AnswerLineOut,
    Bar,
    BeforeMatchOut,
    ClubOut,
    ConceptMapOut,
    ConceptMoveOut,
    DeliveredTime,
    FactOut,
    FeedbackOption,
    FeedbackOut,
    GoalOut,
    LevelRowOut,
    LevelUpOut,
    MapConceptOut,
    MarkerOut,
    MatchOut,
    MomentTime,
    Movement,
    OptionOut,
    PictureOut,
    PlayByPlayOut,
    PlayerNumbersOut,
    PositionOut,
    QuestionOut,
    ReportOut,
    ScoreOut,
    SheetPlayerOut,
    SheetTeamOut,
    SpellOut,
    StrandOut,
    StrandValueOut,
    TeamSheetOut,
    ThresholdsOut,
    TouchOut,
    YourTeam,
)
from btl.concepts.phase import PhaseOfPlay
from btl.league.league import Club, League
from btl.learn.before_match import BeforeMatch, LevelRow
from btl.learn.concept_map import ConceptKey, Thresholds
from btl.learn.curriculum import Curriculum
from btl.learn.evidence import Fact, Picture, percent_points
from btl.learn.knowledge import Delivery
from btl.learn.levels import band_for, level_word
from btl.learn.matches import CatchUp, MatchState, ViewerMatch, score_as_of
from btl.learn.play_by_play import play_by_play
from btl.learn.questions import Form
from btl.learn.report import Break, Report
from btl.learn.session import Asked, Told
from btl.learn.team_sheet import NEXT_STAGE, SheetPlayer, SheetTeam, TeamSheet
from btl.schema.ids import TeamId
from btl.schema.scoreboard import clock, clock_seconds


def question_payload(
    asked: Asked,
    match_number: int,
    home: Club,
    away: Club,
    club: TeamId | None,
    caught: CatchUp,
) -> QuestionOut:
    """The question as the page shows it: its view, its wording, when it is asked and the score.

    ``caught`` is the score as of `score_as_of`: when the question is asked, or just before a
    shot, whose result is the answer.
    """
    view, prompt = asked.view, asked.prompt
    candidate, delivered = prompt.candidate, prompt.delivered
    stands_at = score_as_of(candidate, delivered)
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
        score=ScoreOut(
            home=caught.home,
            away=caught.away,
            clock=clock(stands_at.period_id, stands_at.seconds),
        ),
        catch_up=catch_up_text(caught, home, away),
        play_by_play=play_by_play_payload(asked, home, away),
    )


def play_by_play_payload(asked: Asked, home: Club, away: Club) -> PlayByPlayOut:
    """Who had the ball from where the viewer left off up to the moment the question is about."""
    previous, candidate = asked.previous, asked.prompt.candidate
    delivered = asked.prompt.delivered
    after = None if previous is None else (previous.period_id, previous.time_seconds)
    before = (candidate.period_id, candidate.time_seconds)
    players = {player.player_id: player for player in (*home.squad, *away.squad)}
    return PlayByPlayOut(
        start=0.0 if after is None else clock_seconds(*after),
        end=clock_seconds(delivered.period_id, delivered.time_seconds),
        names_until=clock_seconds(*before),
        spells=[
            SpellOut(
                side="home" if spell.team_id == home.team_id else "away",
                touches=[
                    TouchOut(
                        at=clock_seconds(touch.period_id, touch.time_seconds),
                        player=players[touch.player_id].full_name,
                        number=players[touch.player_id].shirt_number,
                    )
                    for touch in spell.touches
                ],
            )
            for spell in play_by_play(asked.match, after, before)
        ],
    )


def catch_up_text(caught: CatchUp, home: Club, away: Club) -> str | None:
    """The goals since the viewer's last answer and the score, in a sentence or two."""
    if caught.goals is None:
        return None
    score = f"{caught.home}\N{EN DASH}{caught.away}"
    if not caught.goals:
        return f"No goals. It's still {score}."
    said = [
        f"{(home if goal.home else away).name} scored at {goal.clock}"
        + (", an own goal" if goal.own_goal else "")
        for goal in caught.goals
    ]
    return f"{'. '.join(said)}. It's {score}."


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
        at_kickoff=(round(player.at_kickoff[0], 1), round(player.at_kickoff[1], 1)),
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


def report_payload(
    made: Report, league: League, club: TeamId | None, thresholds: Thresholds
) -> ReportOut:
    """The scouting report, with the result from the viewer's side at full time."""
    home, away = league.club(made.home_id), league.club(made.away_id)
    side = your_team(club, home, away)
    full_time = made.at is Break.FULL_TIME
    return ReportOut(
        match_number=made.match_number,
        at=made.at.value,
        home=home.name,
        away=away.name,
        home_code=home.short_name,
        away_code=away.short_name,
        your_team=side,
        home_goals=made.home_goals,
        away_goals=made.away_goals,
        your_result=your_result(side, made.home_goals, made.away_goals) if full_time else None,
        goals=[
            GoalOut(
                clock=goal.clock,
                side="home" if goal.home else "away",
                scorer=goal.scorer,
                own_goal=goal.own_goal,
            )
            for goal in made.goals
        ],
        strands=[
            StrandValueOut(
                key=strand.key,
                name=strand.name,
                concepts=strand.concepts,
                kickoff=strand.kickoff,
                now=strand.now,
            )
            for strand in made.strands
        ],
        concepts=[
            ConceptMoveOut(
                key=move.key,
                name=move.name,
                strand=move.strand,
                before=move.before,
                after=move.after,
                level_before=move.level_before,
                level=move.level,
                band_before=move.band_before,
                band=move.band,
                mastered=move.mastered,
            )
            for move in made.concepts
        ],
        answers=[
            AnswerLineOut(clock=line.clock, concept=line.concept, correct=line.correct)
            for line in made.answers
        ],
        right=sum(line.correct for line in made.answers),
        note=made.note,
        thresholds=thresholds_payload(thresholds),
    )


def movements(before: Mapping[str, float], after: Mapping[str, float]) -> list[Movement]:
    """Each concept's mastery before and after, in the order of ``after``."""
    return [Movement(name=name, before=before[name], after=value) for name, value in after.items()]


def bars(
    mastery: Mapping[ConceptKey, float], names: Mapping[ConceptKey, str], thresholds: Thresholds
) -> list[Bar]:
    """Each concept's mastery now, with its level word and band."""
    return [
        Bar(
            key=key,
            name=names[key],
            value=value,
            level=level_word(value, thresholds),
            band=band_for(value),
        )
        for key, value in mastery.items()
    ]


def before_match_payload(made: BeforeMatch) -> BeforeMatchOut:
    """The flows before a match: First looks, Level-ups, the level list and the unlock note."""
    return BeforeMatchOut(
        match_number=made.match_number,
        first_looks=[_level_row(row) for row in made.first_looks],
        level_ups=[
            LevelUpOut(
                key=up.key,
                name=up.name,
                strand=up.strand,
                strand_name=up.strand_name,
                before=up.before,
                after=up.after,
                level_before=up.level_before,
                level=up.level,
                band_before=up.band_before,
                band=up.band,
                mastered=up.mastered,
            )
            for up in made.level_ups
        ],
        levels=[_level_row(row) for row in made.levels],
        unlock_note=made.unlock_note,
    )


def _level_row(row: LevelRow) -> LevelRowOut:
    return LevelRowOut(
        key=row.key,
        name=row.name,
        strand=row.strand,
        strand_name=row.strand_name,
        mastery=row.mastery,
        level=row.level,
        band=row.band,
        mastered=row.mastered,
        waits_for=list(row.waits_for),
        moved=row.moved,
    )


def concept_map_payload(whole: Curriculum, thresholds: Thresholds) -> ConceptMapOut:
    """The viewer's map of the curriculum."""
    return ConceptMapOut(
        strands=[
            StrandOut(key=strand.key, name=strand.name, description=strand.description)
            for strand in whole.strands
        ],
        tiers=list(whole.tiers),
        concepts=[
            MapConceptOut(
                key=c.key,
                name=c.name,
                strand=c.strand,
                tier=c.tier,
                objective=c.objective,
                prerequisites=list(c.prerequisites),
                askable=c.askable,
                mastery=c.mastery,
                level=c.level,
                band=c.band,
                waits_for=list(c.waits_for),
            )
            for c in whole.concepts
        ],
        thresholds=thresholds_payload(thresholds),
    )


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
