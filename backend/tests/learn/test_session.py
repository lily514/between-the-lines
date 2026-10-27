from dataclasses import dataclass, field, replace
from itertools import pairwise

import pytest

from btl.concepts.phase import PhaseOfPlay
from btl.learn.grader import Answer, ChoiceAnswer
from btl.learn.learner import MATCHES_PER_SESSION
from btl.learn.session import (
    Asked,
    ClubLockedError,
    Course,
    DemoViewer,
    MatchStart,
    PreparedMatch,
    Told,
    choose_club,
    prepare_match,
    start_session,
    watch_match,
)
from btl.schema.ids import TeamId
from btl.store.memory import MemoryLearnerStore
from btl.tutor.templates import TemplateTutor
from tests.fixtures.learning import threat_model

NOW = "2026-10-08T12:00:00+00:00"


def course() -> Course:
    return Course(threat_model(), TemplateTutor())


class StoppedError(Exception):
    """The viewer stopped partway, like pressing Ctrl+C."""


@dataclass
class AlwaysRight:
    """Answers every question correctly; can stop partway through, like Ctrl+C."""

    stop_after: int | None = None
    told: list[Told] = field(default_factory=list[Told])
    asked: list[Asked] = field(default_factory=list[Asked])
    started: list[MatchStart] = field(default_factory=list[MatchStart])
    answered: int = 0

    def begin(self, start: MatchStart) -> None:
        self.started.append(start)

    def ask(self, asked: Asked) -> Answer:
        if self.stop_after is not None and self.answered == self.stop_after:
            raise StoppedError
        self.answered += 1
        self.asked.append(asked)
        return ChoiceAnswer(asked.pack.correct_key)

    def tell(self, told: Told) -> None:
        self.told.append(told)

    def end(self, mastery: dict[str, float], asked: int) -> None:
        pass


def test_the_demo_viewer_learns_over_three_matches() -> None:
    store = MemoryLearnerStore()
    start_session(store, "demo", seed=7)
    viewer = DemoViewer()

    for _ in range(MATCHES_PER_SESSION):
        watch_match(course(), store, "demo", viewer, lambda: NOW)

    stored = store.get("demo")
    assert stored is not None and stored.state.finished
    attempts = stored.state.attempts
    assert [s.match_number for s in viewer.starts] == [1, 2, 3]
    first, last = viewer.starts[0].mastery, viewer.seen[-1].mastery
    asked = {t.pack.concept.name for t in viewer.seen}
    assert asked
    assert all(last[name] > first[name] for name in asked)
    # Nothing is ever asked during a transition.
    assert all(t.pack.timing.delivered_phase is not PhaseOfPlay.TRANSITION for t in viewer.seen)
    # Questions get harder across matches...
    by_match = {n: [a.level for a in attempts if a.match_number == n] for n in (1, 2, 3)}
    assert sum(by_match[3]) / len(by_match[3]) > sum(by_match[1]) / len(by_match[1])
    # ...and within a match, as answers come in: a concept asked again in the same match is
    # asked at a higher level somewhere.
    levels_by_concept: dict[tuple[int, str], list[int]] = {}
    for attempt in attempts:
        levels_by_concept.setdefault((attempt.match_number, attempt.concept), []).append(
            attempt.level
        )
    assert any(
        later > earlier
        for levels in levels_by_concept.values()
        for earlier, later in pairwise(levels)
    )


def test_every_answer_is_saved_as_it_is_given() -> None:
    store = MemoryLearnerStore()
    start_session(store, "lily", seed=3)
    viewer = AlwaysRight()

    watch_match(course(), store, "lily", viewer, lambda: NOW)

    stored = store.get("lily")
    assert stored is not None
    assert len(stored.state.attempts) == len(viewer.told) >= 2
    assert all(a.correct and a.answered_at == NOW for a in stored.state.attempts)
    assert stored.state.match_number == 2


def test_a_stopped_match_carries_on_exactly_where_it_stopped() -> None:
    uninterrupted = MemoryLearnerStore()
    start_session(uninterrupted, "lily", seed=3)
    watch_match(course(), uninterrupted, "lily", AlwaysRight(), lambda: NOW)

    stopped = MemoryLearnerStore()
    start_session(stopped, "lily", seed=3)
    with pytest.raises(StoppedError):
        watch_match(course(), stopped, "lily", AlwaysRight(stop_after=2), lambda: NOW)
    partway = stopped.get("lily")
    assert partway is not None and len(partway.state.attempts) == 2
    resumed = AlwaysRight()
    watch_match(course(), stopped, "lily", resumed, lambda: NOW)

    whole, carried_on = uninterrupted.get("lily"), stopped.get("lily")
    assert whole is not None and carried_on is not None
    assert carried_on.state == whole.state
    assert len(resumed.told) == len(whole.state.attempts) - 2


def test_each_question_knows_where_the_one_before_it_was_asked_even_after_a_stop() -> None:
    store = MemoryLearnerStore()
    start_session(store, "lily", seed=3)
    viewer = AlwaysRight()
    watch_match(course(), store, "lily", viewer, lambda: NOW)
    stopped = MemoryLearnerStore()
    start_session(stopped, "lily", seed=3)
    with pytest.raises(StoppedError):
        watch_match(course(), stopped, "lily", AlwaysRight(stop_after=2), lambda: NOW)
    resumed = AlwaysRight()
    watch_match(course(), stopped, "lily", resumed, lambda: NOW)

    assert viewer.asked[0].previous is None
    for before, after in pairwise(viewer.asked):
        assert after.previous == before.prompt.delivered
    assert resumed.asked[0].previous == viewer.asked[1].prompt.delivered


def test_a_finished_session_or_unknown_viewer_cannot_watch() -> None:
    store = MemoryLearnerStore()
    with pytest.raises(ValueError, match="start a session first"):
        watch_match(course(), store, "nobody", AlwaysRight(), lambda: NOW)

    stored = start_session(store, "done", seed=1)
    store.put(replace(stored.state, match_number=MATCHES_PER_SESSION + 1), stored.etag)
    with pytest.raises(ValueError, match="watched every match"):
        watch_match(course(), store, "done", AlwaysRight(), lambda: NOW)


def test_each_viewer_gets_the_same_three_matches_for_a_seed() -> None:
    fixtures = [course().fixture(seed=7, match_number=n) for n in (1, 2, 3)]

    assert fixtures == [course().fixture(seed=7, match_number=n) for n in (1, 2, 3)]
    assert len({seed for _, _, seed in fixtures}) == 3


def test_a_viewer_without_a_club_keeps_the_matches_from_before_clubs() -> None:
    fixtures = [course().fixture(seed=7, match_number=n) for n in (1, 2, 3)]

    assert [(home.short_name, away.short_name, seed) for home, away, seed in fixtures] == [
        ("RIP", "LUD", 7001),
        ("WHI", "SHE", 7002),
        ("HEX", "PEN", 7003),
    ]


@pytest.mark.parametrize("seed", [0, 7, 3456])
def test_a_viewer_with_a_club_watches_three_different_fixtures_of_that_club(seed: int) -> None:
    shared = course()
    for club in shared.league.clubs:
        fixtures = [shared.fixture(seed, n, club.team_id) for n in (1, 2, 3)]

        assert all(club in (home, away) for home, away, _ in fixtures)
        assert len({(home.team_id, away.team_id) for home, away, _ in fixtures}) == 3


def test_a_club_chosen_before_any_answer_sets_the_matches() -> None:
    shared, store = course(), MemoryLearnerStore()
    start_session(store, "lily", seed=3)
    hexham = shared.league.find_club("HEX")

    chosen = choose_club(shared, store, "lily", hexham.team_id)
    viewer = AlwaysRight()
    for _ in range(MATCHES_PER_SESSION):
        watch_match(shared, store, "lily", viewer, lambda: NOW)

    assert chosen.state.club == hexham.team_id
    assert [hexham.name in (start.home, start.away) for start in viewer.started] == [True] * 3


def test_the_club_cannot_change_once_the_viewer_has_answered() -> None:
    shared, store = course(), MemoryLearnerStore()
    start_session(store, "lily", seed=3)
    with pytest.raises(StoppedError):
        watch_match(shared, store, "lily", AlwaysRight(stop_after=1), lambda: NOW)

    with pytest.raises(ClubLockedError):
        choose_club(shared, store, "lily", TeamId(2))


def test_an_unknown_club_or_viewer_is_refused() -> None:
    shared, store = course(), MemoryLearnerStore()
    start_session(store, "lily", seed=3)

    with pytest.raises(ValueError, match="no club"):
        choose_club(shared, store, "lily", TeamId(0))
    with pytest.raises(ValueError, match="start a session first"):
        choose_club(shared, store, "nobody", TeamId(2))


def test_a_prepared_match_can_be_reused_without_changing_what_is_asked() -> None:
    shared = course()
    cache: dict[tuple[int, int], PreparedMatch] = {}
    calls: list[tuple[int, int]] = []

    def cached(seed: int, number: int, club: TeamId | None) -> PreparedMatch:
        assert club is None
        calls.append((seed, number))
        if (seed, number) not in cache:
            cache[seed, number] = prepare_match(shared, seed, number)
        return cache[seed, number]

    plain, reused = MemoryLearnerStore(), MemoryLearnerStore()
    for store in (plain, reused):
        start_session(store, "lily", seed=3)
    watch_match(shared, plain, "lily", AlwaysRight(), lambda: NOW)
    # Stop after one answer and carry on, so the cached match is used twice.
    with pytest.raises(StoppedError):
        watch_match(shared, reused, "lily", AlwaysRight(stop_after=1), lambda: NOW, cached)
    watch_match(shared, reused, "lily", AlwaysRight(), lambda: NOW, cached)

    plain_state, reused_state = plain.get("lily"), reused.get("lily")
    assert plain_state is not None and reused_state is not None
    assert plain_state.state.attempts == reused_state.state.attempts
    assert calls == [(3, 1), (3, 1)] and len(cache) == 1


@pytest.mark.parametrize("seed", [7, 11])
def test_the_basics_reach_the_viewer_without_giving_the_answer_away(seed: int) -> None:
    store = MemoryLearnerStore()
    start_session(store, "basics", seed=seed)
    viewer = DemoViewer()

    for _ in range(MATCHES_PER_SESSION):
        watch_match(course(), store, "basics", viewer, lambda: NOW)

    asked_about = {asked.pack.concept.key for asked in viewer.asked}
    assert "restarts" in asked_about
    for asked in viewer.asked:
        pack, view = asked.pack, asked.view
        if pack.concept.key == "restarts":
            assert pack.timing.delivery == "live"
            assert pack.timing.delivered_phase is PhaseOfPlay.DEAD_BALL
            assert view.timing.restart is None
            # Only the action that sent the ball out, not the restart.
            assert len(view.picture.path) == 2
            assert len(pack.reveal_path) == 3
        if pack.concept.key == "offside":
            assert pack.reveal_line is not None
        assert "{" not in asked.text
    stored = store.get("basics")
    assert stored is not None
    # The basics are capped, so the other concepts come up early too.
    assert any(
        a.concept in ("line_breaking_pass", "counter_press") and a.match_number <= 2
        for a in stored.state.attempts
    )
