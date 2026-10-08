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

## T5 — Phase timeline (2026-10-08)
**Plan said:** `phase_timeline(match)` splits the match into settled, transition, dead-ball and break segments, from events only. Dead-ball windows run from the stoppage to the restart, and those of 15 s or more fall in a stated band. Planted line-breaks and counter-presses are transitions. It broadly agrees with the simulator's own `phase` field.
**We did:** as planned, with these choices:
- **Names.** The phases are `PhaseOfPlay`, because the schema already has a `Phase` vocabulary: the simulator's per-event label. It keeps the plan's constants: 4 passes, 12 s, and a 15 s minimum window.
- **What counts.** A transition counts completed passes and crosses. A possession that starts with a restart, or with the kickoff after a goal, is settled.
- **Where segments start and end.** Each action's stretch of play runs to the next action. When play stops after an action, the dead ball starts at that action's time, which includes the ball's flight out of play, and runs to the restart. Breaks are zero-length segments after each period's last action.
- **Two views of the result.** The timeline also gives each action's own phase (`phase_of`), which is what the selector needs to place a candidate.

**Measured over 40 seeds** (all moments planted, snapshots off):

| | Result |
|---|---|
| Dead-ball windows of 15 s or more, per match | 25–48, median 35 |
| Simulator transition actions that are also transitions here | 100% (the simulator's rule is narrower: 8 s, with no pass count) |
| Planted moments classified as transitions | 240 of 240 |
| Line-breaks found in settled play, per match (median, before T6's quality filter) | 82 |
| Share of all actions in a transition | 63% |

**Why:** the plan left these details open.
**Affects:**
- **Most moments will be deferred.** 63% of actions are transitions, because simulated possessions usually start with an interception and end before 4 passes or 12 s. That's high, but no real figure has been checked against it yet: StatsBomb's open data could. Most live questions will be line-break predict questions from the settled third of play, and most others will wait for a stoppage.
- **T9's selector** reads `phase_of` and the dead-ball and break segments that are long enough to ask in.

## T6 — Candidates (2026-10-08)
**Plan said:** a natural line break must go forward at least 15 m, add threat, and allow a consistent set of options. Every planted moment must pass. Natural settled line-break candidates per match, per difficulty band, land in a stated band.
**We did:**
- **The forward threshold is 12 m (`MIN_FORWARD`), not 15 m.** The planted line-breaking pass goes exactly 14 m forward (7 m to the line, 7 m beyond), so at 15 m none of them passed. At 12 m every planted moment passes, with a 2 m margin, and the weakest natural ones are still dropped.
- **The third condition, a consistent set of options, moves to T7,** where options are built. A candidate whose options can't satisfy the invariant will be dropped there.
- **Counter-presses have no extra quality rule;** the detector is already strict.
- **The candidate finder never reads planting records,** checked two ways: a test parses the module and finds no `.planted`, and another shows the candidates are identical when a match's planting records are removed.

**Measured over 40 seeds** (12 m, threat added > 0, settled play, planted moments excluded), out of about 208 line-breaks detected per match:

| Difficulty band | Per match: lowest | Median |
|---|---|---|
| All | 36 | 50 |
| Level 1 (0–0.4) | 0 | 1 |
| Level 2 (0.3–0.7) | 14 | 22 |
| Level 3 (0.6–1) | 25 | 37 |

**Why:** the plan's 15 m would have rejected every planted moment, which the plan also required to pass.
**Affects:**
- **Live level-1 questions about line-breaks will be rare,** because natural gaps are seldom wider than 14 m. Level-1 questions are identify questions, so they can come from the planted level-1 moment instead, as a deferred review. T9's selector must allow for that.
- **The band test takes about 8 s,** because line-breaks need full snapshots.
