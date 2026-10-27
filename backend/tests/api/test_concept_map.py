from btl.store.memory import MemoryLearnerStore
from tests.api.test_app import answer, client, next_step, started


def test_the_concept_map_lists_all_twenty_with_levels_for_those_asked_now() -> None:
    api = client(MemoryLearnerStore())
    started(api)

    response = api.get("/api/viewers/demo/concept-map")

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["concepts"]) == 20
    asked_now = [c for c in body["concepts"] if c["askable"]]
    assert len(asked_now) == 6
    assert {c["level"] for c in asked_now} == {"Getting there"}
    later = [c for c in body["concepts"] if not c["askable"]]
    assert all(c["mastery"] is None and c["level"] is None for c in later)
    assert [s["key"] for s in body["strands"]] == ["possession", "pressure", "chances", "game_flow"]
    assert body["thresholds"] == {"unlock": 0.8, "mastery": 0.95}


def test_the_map_moves_with_the_viewer_s_answers() -> None:
    api = client(MemoryLearnerStore())
    started(api)
    question = next_step(api)
    answer(api, question["pack_id"], question["options"][0]["key"])

    body = api.get("/api/viewers/demo/concept-map").json()
    status = api.get("/api/viewers/demo").json()

    on_map = {c["name"]: (c["mastery"], c["level"]) for c in body["concepts"] if c["askable"]}
    assert on_map == {bar["name"]: (bar["value"], bar["level"]) for bar in status["concepts"]}


def test_an_unknown_viewer_has_no_map() -> None:
    assert client(MemoryLearnerStore()).get("/api/viewers/nobody/concept-map").status_code == 404


def test_the_map_without_a_viewer_names_what_is_asked_and_measures_nothing() -> None:
    body = client(MemoryLearnerStore()).get("/api/concept-map").json()

    assert len(body["concepts"]) == 20
    assert sum(c["askable"] for c in body["concepts"]) == 6
    assert all(c["mastery"] is None and c["level"] is None for c in body["concepts"])
