import ast
from pathlib import Path

import btl.concepts
from btl.concepts.base import ConceptId, match_context
from btl.schema.possession import split_possessions
from tests.fixtures.matches import AWAY, six_event_match

# Detectors must work on any data in the event schema, and must find planted moments from their
# football rules alone, so they may not depend on how matches are simulated or planted.
FORBIDDEN = ("btl.sim", "btl.plant", "btl.league", "btl.cli", "btl.io")


def test_the_context_sees_every_action_left_to_right() -> None:
    match = six_event_match()

    ctx = match_context(match)

    away = match.events[3]
    assert away.team_id == AWAY
    assert ctx.events[3].start_x == 105 - away.start_x
    assert ctx.events[0] == match.events[0]
    snapshot = ctx.snapshot(away.action_id)
    assert snapshot is not None
    (actor,) = [p for p in snapshot.positions if p.is_actor]
    assert (actor.x, actor.y) == (ctx.events[3].start_x, ctx.events[3].start_y)


def test_the_context_derives_possessions_from_the_events() -> None:
    match = six_event_match()

    assert match_context(match).possessions == split_possessions(match.events)


def test_concepts_have_readable_labels() -> None:
    assert ConceptId.SWITCH_OF_PLAY.label == "switch of play"


def test_concept_modules_never_import_the_simulator_or_planting() -> None:
    package = Path(btl.concepts.__file__).parent

    for module in package.glob("*.py"):
        tree = ast.parse(module.read_text())
        imported = [
            name
            for node in ast.walk(tree)
            for name in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
        ]
        bad = [name for name in imported if name.startswith(FORBIDDEN)]
        assert not bad, f"{module.name} imports {bad}"
