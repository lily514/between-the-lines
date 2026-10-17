"""The web API's routes: start or carry on, the next question, an answer, and where a viewer stands.

Every request reads the viewer's record, replays their current match with a `WebViewer` and
stops at the next question or straight after the feedback. Preparing a match (simulating it and
finding its moments) is the slow part and is the same for every viewer with that seed, so it
is cached; a request then only replays the selector.

Routes:

- ``POST /api/viewers``: start watching, or carry on (`StartIn` → `StatusOut`).
- ``GET /api/viewers/{viewer_id}``: where a viewer stands (`StatusOut`).
- ``POST /api/viewers/{viewer_id}/next``: the pending question, or the full-time summary when
  the match has no more, which also moves the viewer on to their next match (`NextOut`).
- ``POST /api/viewers/{viewer_id}/answers``: answer the pending question (`AnswerIn` →
  `FeedbackOut`). It never returns the next question: that is a separate request, so each
  request words at most one thing.
"""

import threading
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from btl.api.models import (
    AnswerIn,
    FeedbackOut,
    Fixture,
    FullTimeOut,
    NextOut,
    StartIn,
    StatusOut,
)
from btl.api.payloads import (
    bars,
    feedback_payload,
    movements,
    question_payload,
    thresholds_payload,
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
    Course,
    PreparedMatch,
    prepare_match,
    seed_for_viewer,
    start_session,
    watch_match,
)
from btl.schema.ids import TeamId
from btl.schema.scoreboard import goals
from btl.store.base import LearnerStore, StaleWriteError, Stored, check_viewer_id


def create_app(
    load_course: Callable[[], Course],
    store: LearnerStore,
    now: Callable[[], str],
    frontend: Path | None = None,
) -> FastAPI:
    """The web API over a learner store.

    Args:
        load_course: Gives what every viewer shares; called once, on the first request that
            needs it, so building the app (for its OpenAPI schema, say) costs nothing.
        store: Where learner records are kept: the same records `btl learn` uses.
        now: The time of each answer, as ISO 8601. The server's clock, never `learn/`'s.
        frontend: The built web page (``frontend/dist``), served for every path outside
            ``/api``; None serves the API only.
    """
    app = FastAPI(title="Between the Lines", version="0.1.0")
    # One viewer's requests replay and save the same record, so they take turns. A single lock
    # is enough for a demo server.
    lock = threading.Lock()
    loaded: list[Course] = []
    prepared: dict[tuple[int, int, TeamId | None], PreparedMatch] = {}

    def course() -> Course:
        if not loaded:
            loaded.append(load_course())
        return loaded[0]

    def prepare(seed: int, match_number: int, club: TeamId | None) -> PreparedMatch:
        key = (seed, match_number, club)
        if key not in prepared:
            prepared[key] = prepare_match(course(), seed, match_number, club)
        return prepared[key]

    def stored(viewer_id: str) -> Stored:
        _check(viewer_id)
        found = store.get(viewer_id)
        if found is None:
            raise HTTPException(404, f"no viewer {viewer_id!r}; start watching first")
        return found

    def status(found: Stored) -> StatusOut:
        state = found.state
        fixture = None
        if not state.finished:
            home, away, _ = course().fixture(state.seed, state.match_number, state.club)
            fixture = Fixture(home=home.name, away=away.name)
        return StatusOut(
            viewer_id=state.viewer_id,
            match_number=state.match_number,
            matches=MATCHES_PER_SESSION,
            finished=state.finished,
            fixture=fixture,
            concepts=bars(course().bars(state)),
            thresholds=thresholds_payload(course().model.thresholds),
        )

    @app.post("/api/viewers")
    def start(body: StartIn) -> StatusOut:
        """Start watching, or carry on where the viewer stopped."""
        _check(body.viewer_id)
        seed = seed_for_viewer(body.viewer_id) if body.seed is None else body.seed
        with lock:
            return status(start_session(store, body.viewer_id, seed))

    @app.get("/api/viewers/{viewer_id}")
    def get_status(viewer_id: str) -> StatusOut:
        """Where a viewer stands."""
        with lock:
            return status(stored(viewer_id))

    @app.post("/api/viewers/{viewer_id}/next")
    def next_step(viewer_id: str) -> NextOut:
        """The question waiting to be answered, or full time if the match has no more."""
        with lock:
            state = _watching(stored(viewer_id))
            viewer = WebViewer()
            try:
                after = watch_match(course(), store, viewer_id, viewer, now, prepare)
            except QuestionPendingError as pending:
                start = viewer.start
                assert start is not None
                return question_payload(pending.asked, state.match_number, start.home, start.away)
            except StaleWriteError:
                raise HTTPException(409, "the record changed; try again") from None
            return _full_time(
                viewer, prepare(state.seed, state.match_number, state.club), after.finished
            )

    def _full_time(viewer: WebViewer, match: PreparedMatch, finished: bool) -> FullTimeOut:
        start, ended = viewer.start, viewer.ended
        assert start is not None and ended is not None
        mastery, asked = ended
        scored = goals(match.match)
        return FullTimeOut(
            match_number=start.match_number,
            home=start.home,
            away=start.away,
            home_goals=scored[match.match.home_team_id],
            away_goals=scored[match.match.away_team_id],
            questions=asked,
            concepts=movements(start.mastery, mastery),
            thresholds=thresholds_payload(course().model.thresholds),
            finished=finished,
            next_match=None if finished else start.match_number + 1,
        )

    @app.post("/api/viewers/{viewer_id}/answers")
    def answer(viewer_id: str, body: AnswerIn) -> FeedbackOut:
        """Answer the waiting question and hear the feedback."""
        with lock:
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
