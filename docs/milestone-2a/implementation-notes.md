# Milestone 2a: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Groundwork (2026-10-08)
**Plan said:** a public function `line_breaking.lines_broken(snapshot, team_id, start, end)`, used by the detector; CLI tests pass with `FORCE_COLOR` set.
**We did:**
- `lines_broken` is a method on `LineBreakingPass`, not a module function. It returns the width of the gap the pass goes through in each line it breaks, nearest first, so its length is the number of lines broken. `detect` now calls it.
- A root `tests/conftest.py` clears `FORCE_COLOR` before the CLI is imported. The CLI itself is unchanged.

**Why:**
- The rule's thresholds (how far apart players can be and still form a line, and how many make a line) are fields of the detector. A module function would need them as extra arguments, or would ignore a detector built with other values. The answer options also need the gap widths, not only the count.
- The CLI's rich console is created when `btl.cli.app` is imported, and rich reads `FORCE_COLOR` at that moment, so the tests' per-call environment couldn't undo it. With the variable set, output was coloured, and `btl replay` believed it ran in a terminal: it animated and waited for Enter. Honouring `FORCE_COLOR` is right for real use, so the fix belongs in the tests.

**Affects:** T7 measures answer options with `LineBreakingPass().lines_broken`.

## T2 — Concept map (2026-10-08)
**Plan said:** commit Lily's map with the agreed edits; validation tests, including that every active concept's evidence fields are produced by its evidence builder; only `concept_map.py` reads the file.
**We did:**
- **The agreed edits:**
  - `thresholds` and the per-tier defaults (now `tier_defaults`) moved under `learner_models.bkt`;
  - added `counter_press` and an inactive `phase_of_play`;
  - the line-breaking explanation now also uses the gap width, and line-breaking accepts `identify` questions;
  - `detector:` holds a `ConceptId` value or null;
  - club names in example prompts became `{home_team}` / `{away_team}`;
  - the header comment explains active concepts.
  - The map had 16 concepts, not 17 as said in planning; it now has 18.
- **`transitions` names the counter-attack detector,** because its objective is to "spot a counterattack" and that detector finds exactly those. It isn't active, since no questions exist for it yet.
- **Two more rules than the plan listed:** data requirements must be one of the declared kinds, and no detector may belong to two concepts. A detector's tags must map to a single concept.
- **The evidence-fields check moves to T8,** because evidence builders don't exist yet.
- **Reading the file.** `load_concept_map()` reads the YAML with `importlib.resources`, inside `concept_map.py`, although CLAUDE.md keeps I/O in `io.py`, `store/` and `cli/`. The file ships inside the package and never changes at run time, so reading it is closer to importing code than to reading data. `parse_concept_map(text)` is pure and is what the tests use.
- **Spelling.** The two new concepts follow the map's American spelling ("organize"), not the repo's British, so the file reads consistently.

**Why:** the plan left these details open.
**Affects:**
- **`switch_of_play` has a detector but no concept in the map,** so its tags count towards nothing. That's harmless in 2a; a later milestone can add a concept for it.
- **T8** adds the evidence-fields test.

## T4 — Counter-press difficulty (2026-10-08)
**Plan said:** the detector gives a difficulty from 0 to 1 from the seconds taken to win the ball back, with named thresholds; planted levels are detected in difficulty order over 40 seeds.
**We did:** as planned. Difficulty rises in a straight line from 0 at `QUICK_REGAIN` = 1 s to 1 at `SLOW_REGAIN` = 4 s, rounded to two places. The thresholds were chosen from measurements over 40 seeds:

| Seconds to win back | Lowest | 10th percentile | Median | 90th percentile | Highest | Difficulty, 10th–90th percentile |
|---|---|---|---|---|---|---|
| Planted level 1 | 0.9 | 1.1 | 1.3 | 1.5 | 1.8 | 0.03–0.17 |
| Planted level 2 | 1.6 | 2.0 | 2.3 | 2.6 | 2.8 | 0.33–0.53 |
| Planted level 3 | 2.5 | 2.8 | 3.2 | 3.5 | 3.9 | 0.60–0.84 |
| Natural (27.5 per match) | — | 2.2 | 3.2 | 4.5 | — | 0.40–1.00 |

The three levels never swapped order within a match. The middle 80% of each level lands inside the selector's band for that level (0–0.4, 0.3–0.7, 0.6–1).

**Why:** within about a second the ball has barely left, so the press is unmistakable. By four seconds the opponent has strung passes together, and the regain looks like ordinary defending.

**Affects:**
- **Natural counter-presses are mostly hard** (median difficulty 0.73), so beginners will mostly be asked about the planted level-1 ones. That's fine; it's what they're for.
- **`btl moments` now prints a difficulty for counter-presses**, and its test was updated.
