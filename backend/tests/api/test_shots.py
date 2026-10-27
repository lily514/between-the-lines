"""Shot questions through the API: nothing the page gets before the answer says how a shot ended."""

from typing import Any

from fastapi.testclient import TestClient

from btl.learn.questions import Asks
from btl.learn.session import prepare_match
from btl.schema.ids import ActionId
from btl.schema.scoreboard import goals, match_clock
from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import answer, client, course, next_step

SHOT_ASKS = {Asks.ON_TARGET.value, Asks.WHERE_FROM.value, Asks.HOW_THE_CHANCE_CAME.value}
RESTARTS_A_SHOT_LEADS_TO = ("kickoff", "goal kick", "corner")


def shot_questions(api: TestClient, viewer_id: str, seed: int) -> list[dict[str, Any]]:
    """Every shot question a viewer meets over three matches, answering A each time."""
    api.post("/api/viewers", json={"viewer_id": viewer_id, "seed": seed})
    found: list[dict[str, Any]] = []
    for _ in range(3):
        while (step := next_step(api, viewer_id))["kind"] == "question":
            if step["asks"] in SHOT_ASKS:
                found.append(step)
            answer(api, step["pack_id"], step["options"][0]["key"], viewer_id)
    return found


def test_a_shot_question_tells_the_score_before_the_shot_and_names_no_restart() -> None:
    api = client(MemoryLearnerStore())
    checked = 0
    for seed in (7, 3, 11):
        for question in shot_questions(api, f"fan{seed}", seed):
            match = prepare_match(course(), seed, question["match_number"]).match
            shot = ActionId(question["picture"]["action_id"])
            before = goals(match, before=shot)
            checked += 1

            assert question["form"] == "identify"
            assert question["delivered"]["delivery"] == "deferred"
            assert question["score"]["home"] == before[match.home_team_id]
            assert question["score"]["away"] == before[match.away_team_id]
            assert question["score"]["clock"] == match_clock(match.events[shot])
            assert question["occurred"]["clock"] == question["score"]["clock"]
            # The picture never shows where the shot went: its path ends where the shot starts.
            path = question["picture"]["path"]
            assert path == [] or path[-1] == question["picture"]["ball"]
            assert question["picture"]["mark"] is None
            # The stoppage goes unnamed, wherever the question is asked: a kickoff would mean
            # a goal, a goal kick a miss.
            assert question["delivered"]["restart"] is None
            text = question["text"].lower()
            assert not any(restart in text for restart in RESTARTS_A_SHOT_LEADS_TO)
            catch_up = question["catch_up"]
            if catch_up is not None:
                for goal in [g for g in match.events[shot:] if g.result.name == "SUCCESS"]:
                    assert match_clock(goal) not in catch_up or goal.action_id < shot
    assert checked >= 3
