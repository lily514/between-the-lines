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

## T7 — Questions and options (2026-10-08)
**Plan said:** forms by level and delivery; counter-presses never predicted; wrong options get closer as the level rises. At level 3 the alternatives are "the free teammate and the best forward pass that breaks no line". The options invariant holds over 40 seeds. T6 moved the "consistent set of options" check here.
**We did:**
- **Wording is left to the Tutor.** A question records *what* it asks (`Asks`: where to pass, lines broken, gap width, what they did, seconds to win back), its three options and the picture to show. Pass options are labelled `Pass to {target}`, and the evidence pack fills in the name.
- **Predict alternatives are chosen from fair passes:** passes to teammates that break fewer lines and add no more threat than the real one.
  - **Level 2:** the most backward and the most sideways of them.
  - **Level 3:** the two that add the most threat, the closest in value.

  The plan's "free teammate" is dropped: it could add more threat than the right answer and contradict the feedback. If fewer than two fair passes exist, the moment can't be asked as predict.
- **Identify questions get harder through finer detail:**

  | Level | Line-breaking pass | Counter-press |
  |---|---|---|
  | 1 | How many lines? (none, one, two) | What did they do? (won it back, dropped back, fouled) |
  | 2 | Gap width: under 8 m, 8–14 m, 14 m or more | Seconds to win back: under 2, 2–3.5, 3.5 or more |
  | 3 | Gap width in 3 m ranges around the real one | Seconds in 1-second ranges |

  The true narrow range sits first, second or third at random. Ranges use the detector's own rounded figures, so the shown number and its range always agree.
- **Options are shuffled with a sort key drawn per option.** numpy's `permutation` isn't fully typed in this version, so strict pyright rejects it.
- **`active_concepts(concept_map)`:** the map's concepts whose detector has questions here.
- **Test helpers move to `tests/fixtures/learning.py`,** so each test run simulates the 40-seed matches once and shares them.

**Measured over 40 seeds:** every one of 5,067 line-break candidates, natural and planted, had a fair predict question at both levels 2 and 3, and the invariant held in all of them. In practice no candidate is dropped. Level-3 alternatives are on average closer in threat to the answer than level-2 ones (tested).
**Why:** the plan's level-3 rule could break its own invariant, and the plan left the identify forms open.
**Affects:**
- **T8** turns option facts into displayed `Fact`s and fills `{target}` with the player's name and shirt number.
- **T10's templates** word each `Asks` kind.

## T8 — Evidence pack (2026-10-08)
**Plan said:** `EvidencePack` with `Fact`s (value plus number-only display) and a deterministic `pack_id`; phase, occurred-at, delivered-at and delivery fields; each question form hides exactly its own answer facts; `question_view()` and `feedback_view()`. T2 moved the "every active concept's evidence fields are produced" test here.
**We did:**
- **Context and outcome facts.** Facts are split in two. Context facts are known before answering: the clubs, the score, the clock, and the passer for a line-breaking pass. Outcome facts are everything measured about the play. The question view leaves out **every** outcome fact in every form, not just the one being asked, plus the right answer and the correct flags. That's simpler than a per-form list and can't leak by omission. The feedback view is the whole pack, so there is no `feedback_view()`.
- **Who won the ball back is an outcome fact.** For a counter-press, naming the player who won it back hints at the answer to "what did they do?", so it isn't in the context.
- **How numbers are shown:**
  - Counts as words ("one", "two"), so the map's text reads naturally ("with two players close to the ball").
  - Metres and seconds to one decimal, as the detectors round them, dropping a trailing ".0". So the number shown after answering always falls in the identify range marked right (tested).
  - Threat to two significant figures ("0.29%", "+0.11%"). In midfield, threat values are around 0.3%, so whole percentages showed "0%" both before and after a pass, and different options looked identical.
- **The pack carries the concept's text from the map:** name, objective, the three explanations and the misconceptions. The Tutor needs nothing but the pack and the viewer's level.
- **The picture** holds every player as shirt number, side, position and role, plus the ball, all with the team on the ball attacking left to right. An identify question also gets the play's path.
- **`pressers`** counts the pressing team's outfield players within 10 m of the ball when it is won back, including the one who wins it. **`receiver_zone`** is the pitch third where the pass ends.
- **When a question is asked** arrives as a small `Delivered` record (delivery, time, phase, restart), which T9's selector fills in.
- **`match_clock` and `goals` moved** from `cli/render.py` to a new `schema/scoreboard.py`, so `learn/` doesn't import the CLI. `goals` can now count only the goals before an action. The CLI's output is unchanged.

**Why:** hiding every outcome fact is the safer reading of "never reveals the answer before the viewer commits". The display rules came from looking at real packs.
**Affects:** T10's templates fill slots from `Fact.display`. 2b's Verifier checks the Tutor's slots against the same facts.

## T9 — Live selector, gate and queue (2026-10-08)
**Plan said:** a live selector over the frontier, difficulty bands, 8-minute spacing, at most 4 in-play questions and 2 at each break. Moments in transitions are queued and asked at the next dead ball of 15 s or more, or at a break, re-levelled at delivery, and dropped once mastered. The breaks guarantee a minimum of 2 questions. Occasional level-3 review once everything is mastered. Plus the learner's record.
**We did:** as planned, with these choices:
- **`run_match` walks the match** in the order a viewer meets things: candidate moments, then the dead balls long enough to ask in, then the breaks. It hands each question to an `ask` callback, and reads mastery through another callback at every decision, so an answer changes the very next decision. With the same answers it makes the same decisions, which is what lets T12 resume a session.
- **Queue limits.** At most 2 moments wait at once, never two of the same concept, so a stoppage asks about recent play rather than a backlog. A question that can't be built doesn't count.
- **Review is "occasional"** in a measurable way: with every active concept mastered, review questions are level 3 and at most 1 while the match is on (`REVIEW_CAP`). The breaks can still add theirs.
- **Restart names** for the "Dead ball (goal kick)" opening come from the restart's action type.
- **`LearnerState`** holds the viewer id, the session seed, the match being watched and every `Attempt`. Mastery isn't stored; `model_state()` replays the answers. **The cached model state the plan mentioned is left out:** replaying a session's dozen or so answers takes microseconds.

**Measured over 40 seeds,** with a viewer whose mastery rises 0.15 per answer, and one whose mastery never moves:

| Viewer | Questions per match (lowest, median, highest) | Live | Dead ball | Half-time | Full time |
|---|---|---|---|---|---|
| Always improving | 5, 7, 8 | 9% | 50% | 16% | 26% |
| Never improving | 3, 6, 7 | 5% | 63% | 9% | 23% |

**Why:** the plan left these details open.
**Affects:**
- **More questions than the original "two to four" per match.** The amended plan's caps allow 4 in play plus 2 at each break, up to 8, and the median is 7. Lowering `BREAK_CAP` or `IN_PLAY_CAP` changes that in one place.
- **Live questions are rare** (5–9%), as T5 and T6 predicted. Two-thirds of play is transition, and natural settled line-breaks seldom fit level 1.
- **T12** uses `run_match` with the real question flow as `ask`.

## T10 — Grader, Tutor protocol, slots and templates (2026-10-08)
**Plan said:** `ChoiceGrader`; a `Tutor` protocol; fact slots; a `TemplateTutor` whose wording differs by level, whose deferred questions open with phase context, and whose every slot fills; an import rule for `tutor/`.
**We did:** as planned, with these choices:
- **Slot syntax** (`tutor/slots.py`):
  - `{team}` is a pack fact;
  - `{B.threat_added}` is an option's fact, and `{B.label}` its label;
  - `{answer}` and `{chosen}`, with their facts (`{answer.lines_broken}`), are the right option and the viewer's pick, after answering;
  - `{occurred_at}`, `{delivered_at}` and `{restart}` come from the timing.

  Question wording is filled from the question view alone, so wording that cites an outcome fails with a `SlotError` instead of giving the answer away.
- **The verdict belongs to the grade,** not the Tutor: `Grade.verdict` is "Spot on." or "Not quite.". A Tutor's text can't contradict the grade, because it never says whether the viewer was right.
- **`Answer` is a tagged type** (`ChoiceAnswer`, kind "choice"), so free text can join it later. The knowledge model only sees `Grade.correct`.
- **Feedback:**
  - the concept map's explanation at the viewer's level (level 1 beginner, 2 intermediate, 3 analyst);
  - then a sentence confirming or comparing: for a pass, the right pass's lines broken and threat added against the pick's;
  - after a wrong answer, one of the map's misconceptions, chosen from the pack id so it never changes for the same question.

  The takeaway is the concept's objective from the map.
- **A pass option now carries its receiver's name as a neutral fact (`target`),** so feedback can say "the pass to #9 Niels Meiner". The option's label already showed the name, so nothing new is revealed early.
- **The import rule** is tested by parsing every module in `tutor/`: no imports from `sim`, `value`, `concepts` or `plant`.

**Why:** the plan left the slot syntax and the feedback's structure open.
**Affects:**
- **2b's Verifier** checks a model's slots with the same `question_values` and `feedback_values`, and falls back to these templates.
- **Map text read in a sentence.** Some of the map's wording reads a little stiffly once filled, for example "this one broke one". Rewording the map would fix that.

## T11 — Learner store (2026-10-08)
**Plan said:** a `LearnerStore` protocol with memory and JSON-file implementations; one contract suite run on both (create, get, put, a stale etag refused).
**We did:** as planned, plus:
- **The saved document is shaped like a Cosmos DB item:** `id` and `viewer_id` (the future partition key), `version`, `seed`, `match_number`, and every attempt inside. `to_document` and `from_document` live in `store/base.py`, so Milestone 3's Cosmos store reuses them. A record from another version is refused, like old match files.
- **Viewer ids are kept plain** (lower-case letters, digits, `-` and `_`, up to 64 characters), because they become file names and document ids. That also stops a viewer id like `../escape` from writing outside the folder.
- **Etags.** The JSON store's etag is a hash of the file. The memory store's counts writes. Files are written to a temporary name and then moved into place, so a crash never leaves half a file.

**Why:** the plan left these details open.
**Affects:** T12 keeps learners in `data/learners/` (already gitignored under `backend/data/`). Milestone 3 adds a Cosmos DB store to the contract suite's `STORES`.

## T12 — Session and terminal (2026-10-08)
**Plan said:** `btl learn --viewer NAME` plays the next match (pitch and text, an A/B/C prompt, feedback, the update sentence, progress bars) and resumes across runs; the terminal shows why it's asking now. End to end, the scripted demo viewer watches three matches: nothing is asked in a transition, mastery ends higher for both concepts, and levels rise within and across matches. The threat model is fitted on first use if missing.
**We did:** as planned, with these choices:
- **`learn/session.py` holds the loop.**
  - `Course` is what every viewer shares: the concept map, the BKT model, the league, the threat model and the Tutor.
  - `watch_match` plays one match. For each prompt from the selector, it builds the question and the pack, has the Tutor word it, asks the viewer, grades the answer, saves the record, and tells the viewer the verdict, explanation, takeaway, update sentence and bars.
  - The viewer is anything with `begin`, `ask`, `tell` and `end`: the terminal now, and the web page in 2c.
- **One match per `btl learn` run.** Each viewer's three matches come from a seed, by default derived from their name. `--reset` starts again.
- **Stopping and carrying on.** Answers are saved one by one. On the next run the match is simulated again, and the answers already given are fed back in order instead of being asked. The selector reads mastery as it stood at each point, so it arrives at exactly the next unasked question. A test stops a match after two answers and checks the finished record equals an uninterrupted one.
- **The pitch picture** (`cli/render.py`) gained `show_path` and `marks`:
  - A predict question hides the pass's path, because showing it would give away the answer.
  - It marks each option's receiver with its letter, since an ASCII pitch can't show shirt numbers.
  - An identify question shows the path.
- **A pass option is marked where its receiver stands,** the right one included (this changes T7). Previously the right option sat where the pass was received, off any `o`, which an attentive viewer could spot. Its facts are still measured along the real pass. Packs now carry each option's position (`target_at`) for the pictures, here and in 2c.
- **The question line says why it's asking now:** "Dead ball (goal kick), 14:30 · about play at 11:33", or "30:25 · live, in settled play".
- **Wording tweaks** from watching the demo: "How many defensive lines did that pass go through?", which avoids "Ripon Wardens's", and no automatic number highlighting on learning screens.
- **`btl demo-viewer`** runs the scripted viewer through three matches in memory and prints every question, pick, feedback and bar. It answers one question in three correctly in match 1, one in two in match 2, and all in match 3.

**Measured with the default 200-match threat model, seed 7:** 19 questions over three matches, one of them live (a level-2 predict question in match 3). Both concepts go from 15% to 97%. Three matches take under 2 s.
**Why:** the plan left these details open; the pitch changes came from seeing the demo.
**Affects:**
- **2b** replaces `TemplateTutor` in `Course` with the Foundry Tutor behind the Verifier.
- **2c** writes a web `Viewer` that draws `pack.picture` and `target_at` instead of the ASCII pitch.
