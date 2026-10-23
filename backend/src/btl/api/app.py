"""The web API's routes: start or carry on, the next question, an answer, and where a viewer stands.

Every request reads the viewer's record, replays their current match with a `WebViewer` and
stops at the next question or straight after the feedback. Preparing a match (simulating it and
finding its moments) is the slow part and is the same for every viewer with that seed, so it
is cached; a request then only replays the selector.

Routes:

- ``GET /api/clubs``: the league's clubs (`ClubOut`).
- ``POST /api/viewers``: start watching, or carry on (`StartIn` → `StatusOut`).
- ``GET /api/viewers/{viewer_id}``: where a viewer stands (`StatusOut`).
- ``PUT /api/viewers/{viewer_id}/club``: choose the team to support, until the viewer has
  started watching (`ClubIn` → `StatusOut`).
- ``GET /api/viewers/{viewer_id}/team-sheet``: who's playing in the viewer's next match
  (`TeamSheetOut`).
- ``POST /api/viewers/{viewer_id}/next``: the pending question, or the full-time summary when
  the match has no more, which also moves the viewer on to their next match (`NextOut`).
- ``POST /api/viewers/{viewer_id}/answers``: answer the pending question (`AnswerIn` →
  `FeedbackOut`). It never returns the next question: that is a separate request, so each
  request words at most one thing.
- ``GET /api/health``: the server is up (left out of the schema; the page never calls it).

Requests for different viewers run at the same time; one viewer's requests take turns.
"""

import threading
import weakref
from collections import OrderedDict
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from btl.api.limits import current_viewer
from btl.api.models import (
    AnswerIn,
    ClubIn,
    ClubOut,
    FeedbackOut,
    Fixture,
    FullTimeOut,
    NextOut,
    StartIn,
    StatusOut,
    TeamSheetOut,
)
from btl.api.payloads import (
    bars,
    club_payload,
    feedback_payload,
    movements,
    question_payload,
    team_sheet_payload,
    thresholds_payload,
    your_result,
    your_team,
)
from btl.api.viewer import (
    AnswerOnlyStore,
    BadKeyError,
    FeedbackGivenError,
    NotPendingError,
    QuestionPendingError,
    WebViewer,
)
from btl.learn.learner import MATCHES_PER_SESSION, LearnerState
from btl.learn.session import (
    ClubLockedError,
    Course,
    PreparedMatch,
    choose_club,
    prepare_match,
    seed_for_viewer,
    start_session,
    watch_match,
)
from btl.learn.team_sheet import viewer_sheet
from btl.schema.ids import TeamId
from btl.schema.scoreboard import goals
from btl.store.base import LearnerStore, StaleWriteError, Stored, check_viewer_id

# Prepared matches kept, most recently used first; each is about 2 MB.
PREPARED_SIZE = 32


def create_app(
    load_course: Callable[[], Course],
    store: LearnerStore,
    now: Callable[[], str],
    frontend: Path | None = None,
    prepared_size: int = PREPARED_SIZE,
) -> FastAPI:
    """The web API over a learner store.

    Args:
        load_course: Gives what every viewer shares; called once, on the first request that
            needs it, so building the app (for its OpenAPI schema, say) costs nothing.
        store: Where learner records are kept: the same records `btl learn` uses.
        now: The time of each answer, as ISO 8601. The server's clock, never `learn/`'s.
        frontend: The built web page (``frontend/dist``), served for every path outside
            ``/api``; None serves the API only.
        prepared_size: How many prepared matches to keep; the least recently used goes first.
    """
    app = FastAPI(title="Between the Lines", version="0.1.0")
    # A viewer's requests replay and save the same record, so they take turns; other viewers
    # don't wait for them, even while a model words a question. A lock lives only while a
    # request holds it, so the table doesn't grow with every visitor.
    viewer_locks: weakref.WeakValueDictionary[str, threading.Lock] = weakref.WeakValueDictionary()
    locks_guard = threading.Lock()
    loaded: list[Course] = []
    course_guard = threading.Lock()
    prepared: OrderedDict[tuple[int, int, TeamId | None], PreparedMatch] = OrderedDict()
    prepared_guard = threading.Lock()

    def lock(viewer_id: str) -> threading.Lock:
        with locks_guard:
            found = viewer_locks.get(viewer_id)
            if found is None:
                found = viewer_locks[viewer_id] = threading.Lock()
            return found

    @contextmanager
    def serving(viewer_id: str) -> Generator[None, None, None]:
        # The viewer's turn, and whose request it is, for the model's daily limits.
        with lock(viewer_id):
            token = current_viewer.set(viewer_id)
            try:
                yield
            finally:
                current_viewer.reset(token)

    def course() -> Course:
        with course_guard:
            if not loaded:
                loaded.append(load_course())
            return loaded[0]

    def prepare(seed: int, match_number: int, club: TeamId | None) -> PreparedMatch:
        key = (seed, match_number, club)
        with prepared_guard:
            if key in prepared:
                prepared.move_to_end(key)
                return prepared[key]
        # Preparing takes a fraction of a second, so it happens outside the guard; two viewers
        # meeting the same new match may both prepare it, and get identical results.
        match = prepare_match(course(), seed, match_number, club)
        with prepared_guard:
            prepared[key] = match
            while len(prepared) > prepared_size:
                prepared.popitem(last=False)
        return match

    def stored(viewer_id: str) -> Stored:
        _check(viewer_id)
        found = store.get(viewer_id)
        if found is None:
            raise HTTPException(404, f"no viewer {viewer_id!r}; start watching first")
        return found

    def status(found: Stored) -> StatusOut:
        state = found.state
        league = course().league
        fixture = None
        if not state.finished:
            home, away, _ = course().fixture(state.seed, state.match_number, state.club)
            fixture = Fixture(
                home=home.name,
                away=away.name,
                home_code=home.short_name,
                away_code=away.short_name,
                your_team=your_team(state.club, home, away),
            )
        return StatusOut(
            viewer_id=state.viewer_id,
            match_number=state.match_number,
            matches=MATCHES_PER_SESSION,
            finished=state.finished,
            fixture=fixture,
            club=None if state.club is None else club_payload(league.club(state.club)),
            can_choose_club=state.can_choose_club,
            suggested_club=league.clubs[state.seed % len(league.clubs)].team_id,
            concepts=bars(course().bars(state)),
            thresholds=thresholds_payload(course().model.thresholds),
        )

    def chosen(viewer_id: str, club: int) -> Stored:
        try:
            return choose_club(course(), store, viewer_id, TeamId(club))
        except ClubLockedError:
            raise HTTPException(409, "the team can't change once you've started watching") from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        except StaleWriteError:
            raise HTTPException(409, "the record changed; try again") from None

    @app.get("/api/health", include_in_schema=False)
    def health() -> dict[str, str]:
        """The server is up. It loads nothing, so a probe never waits for a match."""
        return {"status": "ok"}

    @app.get("/api/clubs")
    def clubs() -> list[ClubOut]:
        """The league's clubs, in team id order."""
        return [club_payload(club) for club in course().league.clubs]

    @app.post("/api/viewers")
    def start(body: StartIn) -> StatusOut:
        """Start watching, or carry on where the viewer stopped."""
        _check(body.viewer_id)
        seed = seed_for_viewer(body.viewer_id) if body.seed is None else body.seed
        with serving(body.viewer_id):
            found = start_session(store, body.viewer_id, seed)
            if body.club is not None:
                found = chosen(body.viewer_id, body.club)
            return status(found)

    @app.put("/api/viewers/{viewer_id}/club")
    def put_club(viewer_id: str, body: ClubIn) -> StatusOut:
        """Choose the team to support, before answering anything."""
        with serving(viewer_id):
            stored(viewer_id)
            return status(chosen(viewer_id, body.club))

    @app.get("/api/viewers/{viewer_id}/team-sheet")
    def get_team_sheet(viewer_id: str) -> TeamSheetOut:
        """Who's playing in the viewer's next match, as much as their stage shows."""
        with serving(viewer_id):
            state = _watching(stored(viewer_id))
            return team_sheet_payload(viewer_sheet(course(), state, prepare))

    @app.get("/api/viewers/{viewer_id}")
    def get_status(viewer_id: str) -> StatusOut:
        """Where a viewer stands."""
        with serving(viewer_id):
            return status(stored(viewer_id))

    @app.post("/api/viewers/{viewer_id}/next")
    def next_step(viewer_id: str) -> NextOut:
        """The question waiting to be answered, or full time if the match has no more."""
        with serving(viewer_id):
            state = _watching(stored(viewer_id))
            viewer = WebViewer()
            try:
                after = watch_match(course(), store, viewer_id, viewer, now, prepare)
            except QuestionPendingError as pending:
                match = prepare(state.seed, state.match_number, state.club)
                return question_payload(
                    pending.asked, state.match_number, match.home, match.away, state.club
                )
            except StaleWriteError:
                raise HTTPException(409, "the record changed; try again") from None
            return _full_time(
                viewer,
                prepare(state.seed, state.match_number, state.club),
                state.club,
                after.finished,
            )

    def _full_time(
        viewer: WebViewer, match: PreparedMatch, club: TeamId | None, finished: bool
    ) -> FullTimeOut:
        start, ended = viewer.start, viewer.ended
        assert start is not None and ended is not None
        mastery, asked = ended
        scored = goals(match.match)
        home_goals = scored[match.match.home_team_id]
        away_goals = scored[match.match.away_team_id]
        side = your_team(club, match.home, match.away)
        return FullTimeOut(
            match_number=start.match_number,
            home=start.home,
            away=start.away,
            home_code=match.home.short_name,
            away_code=match.away.short_name,
            your_team=side,
            home_goals=home_goals,
            away_goals=away_goals,
            your_result=your_result(side, home_goals, away_goals),
            questions=asked,
            concepts=movements(start.mastery, mastery),
            thresholds=thresholds_payload(course().model.thresholds),
            finished=finished,
            next_match=None if finished else start.match_number + 1,
        )

    @app.post("/api/viewers/{viewer_id}/answers")
    def answer(viewer_id: str, body: AnswerIn) -> FeedbackOut:
        """Answer the waiting question and hear the feedback."""
        with serving(viewer_id):
            state = _watching(stored(viewer_id))
            before = course().bars(state)
            viewer = WebViewer(answer=(body.pack_id, body.key))
            guarded = AnswerOnlyStore(store, state.match_number)
            try:
                watch_match(course(), guarded, viewer_id, viewer, now, prepare)
            except FeedbackGivenError as given:
                _, _, match_seed = course().fixture(state.seed, state.match_number, state.club)
                return feedback_payload(
                    given.told,
                    before,
                    course().model.thresholds,
                    state.match_number,
                    match_seed,
                )
            except (NotPendingError, QuestionPendingError):
                raise HTTPException(409, "that isn't the question waiting to be answered") from None
            except BadKeyError:
                raise HTTPException(422, f"{body.key!r} isn't one of the options") from None
            except StaleWriteError:
                raise HTTPException(409, "the record changed; try again") from None
            # The guarded store stops the match from ending, so this is never reached.
            raise HTTPException(409, "no question is waiting to be answered")

    if frontend is not None:
        _serve_page(app, frontend)
    return app


def _check(viewer_id: str) -> None:
    try:
        check_viewer_id(viewer_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


def _watching(found: Stored) -> LearnerState:
    if found.state.finished:
        raise HTTPException(409, f"{found.state.viewer_id!r} has watched every match")
    return found.state


def _serve_page(app: FastAPI, folder: Path) -> None:
    """Serve the built page: its files where they exist, and ``index.html`` for other paths."""
    root = folder.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "no such API route")
        wanted = (root / path).resolve()
        if path and wanted.is_file() and wanted.is_relative_to(root):
            return FileResponse(wanted)
        return FileResponse(root / "index.html")
