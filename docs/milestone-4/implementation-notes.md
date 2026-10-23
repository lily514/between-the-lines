# Milestone 4 — Implementation notes

## T1 — Matches and calendar (2026-10-23)

**Plan said:** each match gives its state, plus the score and question count when finished.
**We did:** a match in progress also gives a score, and the match clock it stands at. Both are taken at the last moment
the viewer answered about, never later.
**Why:** the Matches board's "Live now" card shows a score and clock, and the stepped match has no live clock to read
them from. The last moment answered is a point the viewer has already seen, so nothing ahead of them leaks.
**Affects:** T6 shows it on the in-progress card as "at {clock}".

## T2 — Curriculum map and level words (2026-10-23)

**Plan said:** `GET /api/concept-map`, with the viewer's value and level word; settle whether five or six concepts are
askable.
**We did:** the route is `GET /api/viewers/{id}/concept-map`, beside the viewer's other routes. Five concepts are
askable: `ASKABLE` is the detectors with questions (`learn/questions.py`), and `counter_attack` has none, so
Transitions is "coming later" on the map, as the handoff says. Level words live in `learn/levels.py` and follow
`level_for`, with "Mastered" at the mastery threshold.
**Why:** the map carries the viewer's values, so it needs the viewer, like the matches and team sheet.
**Affects:** T7 calls the viewer's route.
