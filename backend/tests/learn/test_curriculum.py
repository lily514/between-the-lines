from functools import cache

from btl.learn.concept_map import ConceptKey
from btl.learn.curriculum import curriculum, strand_name
from btl.learn.learner import LearnerState
from btl.learn.levels import Band
from btl.learn.session import Course
from btl.tutor.templates import TemplateTutor
from tests.api.test_app import SEED, demo_attempts
from tests.fixtures.learning import threat_model

ASKED_NOW = {
    "Tackles and turnovers",
    "Shots and goals",
    "Restarts",
    "Offside",
    "Fouls and cards",
    "Transitions and counterattacks",
    "Line-breaking passes",
    "Counter-pressing",
}


@cache
def course() -> Course:
    return Course(threat_model(), TemplateTutor())


def test_the_map_shows_every_concept_and_measures_only_those_asked_now() -> None:
    whole = curriculum(course(), LearnerState("new", SEED))

    assert len(whole.concepts) == len(course().concept_map.concepts) == 20
    assert {c.name for c in whole.concepts if c.askable} == ASKED_NOW
    for concept in whole.concepts:
        measured = concept.mastery is not None and concept.level is not None
        assert measured is concept.askable


def test_a_new_viewer_is_getting_there_on_everything_asked_now() -> None:
    whole = curriculum(course(), LearnerState("new", SEED))

    assert {c.level for c in whole.concepts if c.askable} == {"Getting there"}
    assert {c.band for c in whole.concepts if c.askable} == {Band.GETTING_THERE}
    assert all(c.band is None for c in whole.concepts if not c.askable)


def test_a_concept_says_which_askable_prerequisites_it_still_waits_for() -> None:
    new = {str(c.key): c for c in curriculum(course(), LearnerState("new", SEED)).concepts}
    no_viewer = {str(c.key): c for c in curriculum(course(), None).concepts}

    assert new["transitions"].waits_for == ("Tackles and turnovers", "Restarts")
    assert new["counter_press"].waits_for == ("Tackles and turnovers",)
    assert new["line_breaking_pass"].waits_for == ()
    assert new["tackles"].waits_for == ()
    # Coming later: nothing is measured, so nothing waits.
    assert new["pressing"].waits_for == () and new["game_state"].waits_for == ()
    assert {k: c.waits_for for k, c in no_viewer.items()} == {
        k: c.waits_for for k, c in new.items()
    }


def test_a_prerequisite_unlocks_at_the_threshold() -> None:
    state = LearnerState("demo", SEED, attempts=demo_attempts())
    mastery = course().mastery(state)
    whole = {str(c.key): c for c in curriculum(course(), state).concepts}

    unlock = course().model.thresholds.unlock
    expected = tuple(
        name
        for key, name in (("tackles", "Tackles and turnovers"), ("restarts", "Restarts"))
        if mastery[ConceptKey(key)] < unlock
    )
    assert whole["transitions"].waits_for == expected
    assert whole["counter_press"].waits_for == (
        () if mastery[ConceptKey("tackles")] >= unlock else ("Tackles and turnovers",)
    )


def test_the_map_s_values_are_the_progress_bars() -> None:
    state = LearnerState("demo", SEED, attempts=demo_attempts())

    whole = curriculum(course(), state)

    assert {c.name: c.mastery for c in whole.concepts if c.askable} == course().bars(state)


def test_strands_and_tiers_come_from_the_concept_map_in_order() -> None:
    whole = curriculum(course(), LearnerState("new", SEED))

    assert [s.name for s in whole.strands] == ["Possession", "Pressure", "Chances", "Game flow"]
    assert whole.tiers == ("Newcomer", "Casual fan", "Engaged fan", "Analyst")
    keys = {c.key for c in whole.concepts}
    assert all(set(c.prerequisites) <= keys for c in whole.concepts)


def test_a_strand_s_name_is_its_key_in_words() -> None:
    assert strand_name("game_flow") == "Game flow"
