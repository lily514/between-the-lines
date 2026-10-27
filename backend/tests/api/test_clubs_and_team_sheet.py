"""The API's club choice and team sheet: picking a team, and who's playing before a match."""

from typing import Any

from fastapi.testclient import TestClient

from btl.learn.learner import MATCHES_PER_SESSION
from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import SEED, answer, client, course, demo_attempts, next_step, started

HEXHAM = 2


def start(api: TestClient, viewer_id: str = "lily", **extra: Any) -> Any:
    return api.post("/api/viewers", json={"viewer_id": viewer_id, "seed": SEED, **extra})


def answer_first_question(api: TestClient, viewer_id: str = "lily") -> None:
    question = next_step(api, viewer_id)
    assert question["kind"] == "question"
    response = answer(api, question["pack_id"], question["options"][0]["key"], viewer_id)
    assert response.status_code == 200, response.text


def test_the_clubs_are_listed_by_id_name_and_code() -> None:
    clubs = client(MemoryLearnerStore()).get("/api/clubs").json()

    assert len(clubs) == len(course().league.clubs)
    assert clubs[HEXHAM - 1] == {"team_id": HEXHAM, "name": "Hexham Anchors", "code": "HEX"}


def test_a_new_viewer_has_no_club_yet_and_a_suggestion() -> None:
    status = start(client(MemoryLearnerStore())).json()

    assert status["club"] is None and status["can_choose_club"] is True
    assert status["suggested_club"] in {club.team_id for club in course().league.clubs}
    assert status["fixture"]["your_team"] is None
    assert status["fixture"]["home_code"] and status["fixture"]["away_code"]


def test_starting_with_a_club_makes_the_matches_its_fixtures() -> None:
    status = start(client(MemoryLearnerStore()), club=HEXHAM).json()

    assert status["club"]["code"] == "HEX"
    fixture = status["fixture"]
    assert "Hexham Anchors" in (fixture["home"], fixture["away"])
    assert fixture["your_team"] == ("home" if fixture["home"] == "Hexham Anchors" else "away")


def test_the_club_can_change_until_the_first_answer() -> None:
    api = client(MemoryLearnerStore())
    start(api)

    changed = api.put("/api/viewers/lily/club", json={"club": HEXHAM})
    answer_first_question(api)
    too_late = api.put("/api/viewers/lily/club", json={"club": 5})
    same = start(api, club=HEXHAM)

    assert changed.status_code == 200 and changed.json()["club"]["team_id"] == HEXHAM
    assert too_late.status_code == 409 and "started watching" in too_late.json()["detail"]
    assert same.status_code == 200 and same.json()["can_choose_club"] is False
    assert start(api, club=5).status_code == 409


def test_an_unknown_club_or_viewer_is_refused() -> None:
    api = client(MemoryLearnerStore())
    start(api)

    assert api.put("/api/viewers/lily/club", json={"club": 99}).status_code == 422
    assert api.put("/api/viewers/nobody/club", json={"club": HEXHAM}).status_code == 404
    assert api.get("/api/viewers/nobody/team-sheet").status_code == 404


def test_questions_and_full_time_say_which_side_is_yours() -> None:
    api = client(MemoryLearnerStore())
    status = start(api, club=HEXHAM).json()
    side = status["fixture"]["your_team"]

    question = next_step(api, "lily")

    assert question["your_team"] == side
    assert (question["home_code"], question["away_code"]) == (
        status["fixture"]["home_code"],
        status["fixture"]["away_code"],
    )
    step = question
    while step["kind"] == "question":
        assert answer(api, step["pack_id"], step["options"][0]["key"], "lily").status_code == 200
        step = next_step(api, "lily")
    assert step["kind"] == "full_time" and step["your_team"] == side
    ours, theirs = step["home_goals"], step["away_goals"]
    if side == "away":
        ours, theirs = theirs, ours
    expected = "won" if ours > theirs else "drew" if ours == theirs else "lost"
    assert step["your_result"] == expected
    assert step["home_code"] == question["home_code"]


def test_a_beginner_s_team_sheet_lists_both_elevens_their_team_first() -> None:
    api = client(MemoryLearnerStore())
    start(api, club=HEXHAM)

    sheet = api.get("/api/viewers/lily/team-sheet").json()

    assert sheet["match_number"] == 1 and sheet["stage"] == 1
    assert sheet["next_stage"] == "Get to Solid in any concept to see formations and position tags."
    yours, theirs = sheet["teams"]
    assert (yours["code"], yours["yours"], theirs["yours"]) == ("HEX", True, False)
    assert len(yours["players"]) == len(theirs["players"]) == 11
    keeper = yours["players"][0]
    assert keeper["role"] == "GK" and keeper["position"]["name"] == "Goalkeeper"
    assert keeper["position"]["description"]
    assert len(keeper["at_kickoff"]) == 2 and keeper["numbers"] is None
    assert yours["formation"] is None and yours["matches_watched"] is None


def test_a_finished_viewer_has_no_team_sheet() -> None:
    api = client(MemoryLearnerStore())
    start(api, viewer_id="demo")
    for _ in range(MATCHES_PER_SESSION):
        while (step := next_step(api, "demo"))["kind"] == "question":
            assert (
                answer(api, step["pack_id"], step["options"][0]["key"], "demo").status_code == 200
            )

    assert api.get("/api/viewers/demo/team-sheet").status_code == 409


def test_the_team_sheet_never_uses_the_match_being_watched() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    expected = list(demo_attempts())
    # Play the demo viewer's answers through matches 1 and 2.
    while (step := next_step(api))["kind"] == "question" or step["next_match"] != 3:
        if step["kind"] == "question":
            assert answer(api, step["pack_id"], expected.pop(0).chosen).status_code == 200

    before = api.get("/api/viewers/demo/team-sheet").json()
    question = next_step(api)
    answer(api, question["pack_id"], expected.pop(0).chosen)
    after = api.get("/api/viewers/demo/team-sheet").json()

    assert before["match_number"] == 3 and before["stage"] == 3
    watched = {team["code"]: team["matches_watched"] for team in before["teams"]}
    fixtures = [course().fixture(SEED, n) for n in (1, 2)]
    for code, count in watched.items():
        assert count == sum(
            code in (home.short_name, away.short_name) for home, away, _ in fixtures
        )
    numbers = [p["numbers"] for t in before["teams"] for p in t["players"]]
    assert all(n is None or 1 <= n["matches"] <= 2 for n in numbers)
    assert [t["players"] for t in after["teams"]] == [t["players"] for t in before["teams"]]
