# Milestone 5 — Implementation notes

## Summary

**Biggest changes:**
- **Three more concepts are asked about:** Tackles and turnovers (`ball_win` detector), Shots and goals (`shot`) and
  Transitions and counter-attacks (the `counter_attack` detector, with counter-attacks now planted in every match).
  Eight of twenty are active; the tier-0 cap is five a match.
- **Levels have bands and icons.** The API sends each concept's band (`getting_there`, `solid`, `sharp`) and what it
  still waits for; the page shows a quarter, half or full disc beside every level word, a tick for Mastered, and
  "Unlocks after …" for a locked concept. The team sheet's gate copy says Solid and Sharp.
- **Scenes.** One real moment per active concept (`btl scene-fixtures`, committed and checked) drives an animated
  scene with a layer per level, on a 5 s CSS loop with Pause and a reduced-motion still frame. Specs place every
  label from the fixture's players, path and facts.
- **Story flows.** The welcome is a step per strand with its scene; before a match, a First look introduces concepts
  new to the viewer (record version 4 remembers which) and a Level-up tells each concept that moved up, then the
  level list and the unlock note.

**What was cut:** nothing from the plan. The Tutor evaluation's recorded replies were re-recorded with the model
after the run (see "After T16" below).

**What carries over:**
- The demo viewer (seed 7, answering as the terminal demo does) never reaches Transitions or Counter-pressing in
  three matches, by the accepted gating; a viewer answering well reaches both by match 2 (T7).
- Headless Chrome here enforces a 500 px minimum viewport; `tmp/cdp-shot.mjs` drives screenshots over the
  DevTools protocol instead (T12, T15). It is not in the repo.
- The hand-tuned question and feedback fixtures are unchanged from Milestone 4 apart from the new level fields;
  their matches have moved on since they were captured (T10).

## T0 — Plan and design reference (2026-10-26)

**Plan said:** `design/` holds the handoff `.md` and the "Welcome redesign" export, unchanged.
**We did:** both are copied byte for byte, named `HANDOFF.md` (as every earlier milestone's handoff is) and
`Welcome-redesign.html`. The export bundles its boards as gzip-and-base64 pages inside a
`<script type="__bundler/manifest">`; nothing in the repo reads it, so it stays as delivered. Boards B2, B3 and B4
are one component with a different default flow (Before match 2, Before match 3, First look), so the three
share one scene catalogue and one step layout.
**Why:** full-word file names are the docs rule; the export is a reference, not data the app uses.
**Affects:** nothing.

## T1 — Tier-0 cap (2026-10-26)

**Plan said:** `TIER0_MATCH_CAP` 3 → 5, with its tests.
**We did:** as planned. The cap test now needs five basics in one match, and the in-play cap is four, so the
fifth comes at half-time as a saved review (advantage after a foul): the test builds exactly that.
**Why:** a match cap that never binds would be untested.
**Affects:** nothing.

## T2 — Ball-win detector (2026-10-26)

**Plan said:** evidence is how it was won and metres from its own goal; difficulty is higher near a third line.
**We did:** as planned. "How it was won" is a `WonWith` value in the evidence (tackle, interception, the keeper,
or a loose ball for any other action that opens a possession, such as a clearance), since evidence holds
numbers. `pitch_third` turns the metres into the own, middle or attacking third, one definition for the
questions and the facts. Difficulty is 0 at 12 m or more from a third's line, 1 on it.
**Why:** the level-2 question is which third, so the hard moments are the ones near a line.
**Affects:** T5 reads `WonWith` and `pitch_third`.

## T3 — Shot detector (2026-10-26)

**Plan said:** evidence is the outcome, the zone and the previous action's type; difficulty is how near the
end point is to a post.
**We did:** as planned, with `ShotOutcome`, `ShotZone` and `ChanceFrom` values in the evidence. The chance's
source is the shooting team's last action in the same possession: a cross (open play, corner or free-kick
cross), a pass (including short set pieces), a dribble, or a loose ball when there is none; a direct free
kick is its own source. The span runs from that source to the shot. Penalties are left out: the foul question
already covers them. A blocked shot, which the simulator never produces, would read as off target.
**Why:** the level-3 question offers cross, pass, dribble or free kick, so the source needs a name even when
the shot opens the possession.
**Affects:** T6 must not show the shot's end before the viewer answers (the span ends at the shot).

## T4 — Plant counter-attacks (2026-10-26)

**Plan said:** a `CounterAttackTemplate` modelled on `CounterPressTemplate`, 7–8 s at level 1, 9–10 s at level 2,
11–12 s at level 3, then `PlayOn`; a calibration band; every match's events change.
**We did:**
- **The template ends with a touch in the box.** The ball is won (22–50 m from the team's own goal), played
  forward, played into the box, and the receiver takes a scripted 2 m touch there; `PlayOn` carries on from
  that touch. The detector measures to the first action in the box, so scripting that action makes the
  seconds exact; left to the simulator, a foul in the box (rare) would have put the first action after a
  55 s penalty delay. The planted moment's answer is the touch, not the win: `test_every_planted_moment…`
  checks a counter-attack's answer against the tag's span end, since the key action stays the win.
- **The time is made with how long players hold the ball.** The passes' flight is fixed by the distance, so
  the level's seconds are reached by splitting the rest between the two players' touches.
- **Planter targets moved to the start of each share.** With nine moments, the last target fell at about
  83:00, two minutes before the quiet end, and 3 matches in 60 missed their level-3 counter-attack. Targets
  at `index / count` instead of `(index + 0.5) / count` give the last moment eight minutes; 0 in 60 miss now.
- **The band is wide.** Plain simulated matches hold 0.7 counter-attacks a match on average (median 0), fewer
  than real football's few; the band checks the mean stays between 0.3 and 4 and no match goes past 8. The
  designed matches plant three more, which is what the questions rely on.
- **The Tutor evaluation's recorded replies no longer cover every prompt.** `tests/fixtures/tutor-replies.json`
  holds real model replies keyed by the exact request; the evaluation samples seed 0's designed matches, which
  have changed, so some prompts have no recorded reply and the tests in `tests/tutor/test_evaluation.py`
  fail. Re-recording needs the Foundry model, which this run never calls. Done after T16 (see "After T16").
- **The page's captured fixtures are stale** (`frontend/src/test-fixtures/*.json`): they are real payloads from
  seed 7's matches, which have changed. T15 refreshes them from the running API.
- These four notes were written with their tasks but reached the file only after T5: the command that appended
  them was refused by the session's worktree guard, and the T4 commit carried the file unchanged.
**Why:** exact seconds and a reliable last moment matter more than mirroring the counter-press template's
hand-over ending; the recording can only be made with the model.
**Affects:** T7 (Transitions questions get three planted moments a match); T15 (fixtures); Lily (the recording).

## T5 — Tackles questions (2026-10-27)

**Plan said:** new `Asks`, `QUESTIONS`, `FACTS`, `SHOWN` and templates; check how gating Counter-pressing on Tackles
affects the session test.
**We did:**
- Three identify questions, never live: a ball win opens a transition, so the selector already holds it for a
  stoppage. `SHOWN` keeps the default (the span: the loser's last action and the win), so the picture shows
  where the ball was won; that is what the level-2 question asks, and the difficulty is highest near a third's
  line for the same reason.
- The level-3 options are three statements: the reason for the moment's third, the map's misconception
  ("Winning the ball deep in your own half is just as useful as winning it high") and another third's reason. A
  test keeps the distractor equal to the map's text.
- `high_recoveries` and `avg_high_recoveries` are counted from the match's ball wins up to the moment (both
  teams' mean for the average), plus `metres_from_own_goal` for the feedback.
- **The Verifier now allows the thirds of the pitch.** "third" is on its number-word list, so the map's own
  analyst text ("in the attacking third") failed `bare_number`. "own/middle/attacking/defensive/final third"
  join the football phrases, as "second half" did; `docs/milestone-2b/verifier.md` says so.
- **The demo test pairs attempts by concept.** `test_the_demo_viewer_learns_over_three_matches` compared
  consecutive attempts and only counted a rise when the same concept came twice in a row; with eight concepts
  that no longer happens, though Tackles still goes from level 1 to 2 within match 3. It now compares each
  concept's successive levels within a match, which is what it meant.
- **Gating, measured.** Over the demo viewer's three matches (seed 7) Tackles reaches 0.84 only with its last
  answer, so Counter-pressing is never asked: its mastery stays at its prior. Lily accepted this gating; the plan's
  "the demo viewer asks all eight concepts" won't hold for seed 7 as the demo script stands. The session test
  still passes (Line-breaking passes reaches the viewer in match 2).
**Why:** the map's wording is the source of truth, so the Verifier bends, not the map.
**Affects:** T7 (Transitions waits for Tackles too); T16's transcript; an open question for Lily on the demo.

## T6 — Shots questions (2026-10-27)

**Plan said:** as T5, plus the no-giveaway rule: `ASKED_WHEN` afterwards, the score and catch-up before the
shot, no restart named, `mark`; a test plays shot questions through the API.
**We did:**
- Three identify questions, only ever reviewed (`AskedWhen.AFTERWARDS`). Level 1 asks "What came of it?"
  rather than "Was it on target?", because "target" is a word in the option "Off target" and the Verifier's
  hint check rightly refuses a question that uses an option's own word.
- **The score stands just before the shot.** `score_as_of` (`learn/matches.py`) gives a question's score time:
  delivery for every other concept, the shot's own moment for a shot, counting goals from actions before it.
  The API route and the payload both use it, so the step's score, its clock and the catch-up all stop before the
  shot.
- **No restart is ever named for a shot.** The selector already dropped the name when the stoppage followed the
  moment itself; the API test found a shot asked at a later kickoff (another goal's) with "kickoff" in the
  text, which still says a goal was scored. `HIDES_THE_RESTART` in the selector now blanks the restart for every
  shot review, wherever it is asked.
- **The picture stops at the shot's start.** `SHOWN` draws the span up to the action before the shot (the pass
  or cross arriving), and nothing for a shot that opens a possession; there is no `mark` before answering. The
  plan's "the picture marks where the ball ended" would have shown on target or not, which is the level-1
  answer, so the end point waits for the feedback's reveal path.
- **Facts:** `shots`, `shots_on_target` and `opp_shots` are counted up to and including the shot, so the map's
  text reads true at that moment; `metres_from_goal` joins them for the feedback.
- **The review queue yields to rarer concepts.** With every open-play turnover and every shot a review
  candidate, the two-slot queue was full of basics by the time a match's one planted level-1 line-breaking
  moment came along, and the demo viewer met no line-breaking pass in matches 1 and 2
  (`test_the_basics_reach_the_viewer…` failed). `_save_for_a_stoppage` now drops a queued moment whose concept
  is no longer wanted and lets a rarer concept's moment take a queued basic's place: basics come round every
  few minutes, which is the reason they are capped. Seed 7's demo viewer now meets line-breaking in match 1.
- **Two more Verifier adjustments for the map's own text:** the echo check now reads a comma as the end of a
  clause (the Shots objective says "shots, shots on target"), and "you"/"your" join the label stopwords beside
  "their" and "his" (the Tackles misconception says "your own half", which made the fake model's wording a hint).
  `docs/milestone-2b/verifier.md` says both.
- `strand_values` in `learn/report.py` is public now, so the radar's "no value for a strand with nothing asked"
  rule keeps a test although every strand has a concept asked about.
**Why:** a shot's result is its answer, and every path to it (score, catch-up, restart, picture) had to close.
**Affects:** T7 and T15 (the queue change moves the demo transcript and the captured fixtures again).

## T7 — Transitions questions (2026-10-27)

**Plan said:** as T5; facts `seconds_to_box`, `transition_shots` and `settled_shots` so far from `concepts/phase.py`;
`PACK_VERSION` bumped once.
**We did:** as planned (`PACK_VERSION` is 4), with these details:
- The level-2 ranges are "Under 8 s", "8 to 10 s" and "10 s or more", around the planted levels, through the
  same range helper the counter-press regain question uses.
- The level-3 distractor is the map's "A counterattack is any fast attack" (the map spells it without a
  hyphen; a test keeps them equal). The question says "counter-attack", which the Verifier's hint check reads
  as a different word, and the asks value "why a counter-attack" makes it part of the question's subject.
- **Nothing of the run is pictured before answering.** The level-1 answer is that the team went straight for
  goal, so the picture shows the win only; the reveal path after answering runs from the win to the box.
- `transition_shots` and `settled_shots` count the team's shots up to the end of the counter-attack by the
  phase each shot was taken in; `won_metres_from_own_goal` joins them for the feedback.

**Enough moments** (candidates a match by concept and level band, min / median / mean over seeds 0–19):

| Concept | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| tackles | 126 / 144.5 / 142.6 | 30 / 48 / 46.5 | 34 / 50.5 / 49.2 |
| shots_and_goals | 11 / 16 / 15.0 | 2 / 6 / 5.0 | 2 / 3 / 3.0 |
| restarts | 41 / 53 / 53.1 | 20 / 27.5 / 28.4 | 1 / 8 / 7.0 |
| offside | 6 / 10 / 10.4 | 5 / 10.5 / 11.0 | 4 / 9.5 / 9.6 |
| fouls_and_cards | 10 / 17 / 16.9 | 3 / 8.5 / 8.4 | 0 / 3.5 / 3.7 |
| transitions | 1 / 1 / 1.2 | 1 / 1 / 1.2 | 1 / 1 / 1.3 |
| line_breaking_pass | 1 / 3.5 / 3.7 | 26 / 40.5 / 40.9 | 72 / 79 / 81.2 |
| counter_press | 1 / 3 / 3.8 | 5 / 7 / 8.2 | 7 / 13.5 / 13.8 |

Every concept has at least one moment at every level in every match except fouls at level 3 (as before M5).
Transitions has exactly the planted three in most matches: the simulator's open play rarely counter-attacks.

**The demo viewer, seed 7, after T7** (match · concept · level · right or wrong · delivery):

```
1 restarts 1 right live            2 restarts 1 right live           3 fouls_and_cards 2 right live
1 fouls_and_cards 1 wrong live     2 fouls_and_cards 1 wrong live    3 tackles 1 right deferred
1 restarts 2 wrong live            2 fouls_and_cards 1 right live    3 line_breaking_pass 1 right deferred
1 line_breaking_pass 1 right def.  2 line_breaking_pass 1 wrong def. 3 line_breaking_pass 2 right deferred
1 line_breaking_pass 2 wrong def.  2 shots_and_goals 1 right def.    3 line_breaking_pass 3 right deferred
1 tackles 1 wrong deferred         2 tackles 2 wrong deferred        3 tackles 2 right deferred
1 tackles 1 right deferred                                           3 line_breaking_pass 3 right deferred
                                                                     3 offside 1 right deferred
```

Final mastery: Tackles 0.88, Shots 0.67, Restarts 0.71, Offside 0.67, Fouls 0.82, Transitions 0.25 (its
prior), Line-breaking 0.97, Counter-pressing 0.15 (its prior). **Six of the eight concepts are asked; Transitions
(waits for Restarts and Tackles at 0.8) and Counter-pressing (waits for Tackles) are never reached**, because
the demo script gets one in three right in match 1 and one in two in match 2. Lily accepted the gating; whether
the demo script should answer the basics better, so the README's demo shows all eight, is for her to decide.
**Why:** the map's prerequisites are the source of truth for the frontier.
**Affects:** T16's summary; an open question for Lily.

## T8 — Bands, locks, introduced, and the before-match API (2026-10-27)

**Plan said:** `band` and `key` on `Bar`, `MapConceptOut` and `ConceptMoveOut`; `waits_for` on `MapConceptOut` and
the level rows; `LearnerState.introduced` with version 4 and the store's fallback; `POST …/introduced`;
`GET …/before-match` with `first_looks`, `level_ups`, `levels` and `unlock_note`.
**We did:** as planned, with these details:
- `Band` (`getting_there`, `solid`, `sharp`) and `band_for` live beside `level_word` in `learn/levels.py`; `band_rose`
  is what a Level-up step is shown for, so a two-band jump is one step by construction.
- `waits_for` names the askable prerequisites in force whose mastery is under the unlock threshold, in map order.
  Without a viewer (the map before the welcome) a new viewer's priors stand in, so the map shows the same locks a
  new viewer would get: Transitions waits for Tackles and Restarts, Counter-pressing for Tackles.
- **Who marks a new viewer introduced.** The record is model-free, so `start_session` takes the concepts already
  met: the API's start route and the CLI pass `course.active`, since the welcome covers them all. A record created
  without any (the tests' plain `start_session`) gets a First look at everything.
- The flows' data is built in `learn/before_match.py`, from the full-time report of the last match (Level-ups and
  the "new" marks), the record (First looks) and the team-sheet stage before and after the last match (the unlock
  note, with `STAGE_OPENED` copy beside `NEXT_STAGE` in `learn/team_sheet.py`).
- `POST …/introduced` returns the viewer's status, like the other record changes, and refuses a concept that
  isn't asked about now (422). `GET …/before-match` is 409 for a viewer who has finished, like the team sheet.
- The page's client gained `getBeforeMatch` and `markIntroduced`; the hand-built status fixture carries `key`
  and `band`. The captured JSON fixtures stay as they are until T15 (they are cast, so the types don't bite).
**Why:** the browser never applies a cut-off, so every level it shows arrives as a band from the API.
**Affects:** T10 (icons switch on `band`, locks on `waits_for`), T13 (the flows), T15 (fixtures).

## T9 — Scene fixtures (2026-10-27)

**Plan said:** `btl scene-fixtures` writes one JSON per active concept from a real moment in seed 7's matches: the
evidence pack with every evidence field filled, the snapshot at the key frame, the play's path with timestamps; a
freshness test; the command in `docs/setup.md` and `CLAUDE.md`.
**We did:** as planned, with these choices:
- **A fixed threat fit.** The pack's threat facts depend on the model, so the fixtures are scored with the same
  deterministic 20-match fit the tests use (`fixture_course`), not the saved 200-match model; otherwise the
  freshness test could only check them by fitting 200 matches. The numbers are real for that fit and serve as
  illustrations on the page, which is what the handoff asked for in place of its made-up ones.
- **Which moment.** The candidate nearest difficulty 0.5, among those that tell the story best: an offside call
  for Offside, a goal-line restart for Restarts, a foul that stopped play, a ball won in the middle third, and a
  counter-attack won by an outfield player (the first pick was the keeper gathering a metre from goal).
- **What a fixture holds**, beyond the plan: the concept's evidence field list, the match and the moment's
  evidence, and `questions`: the template Tutor's wording at each level with its options and the right key, so
  the example card on a step can show the question that moment really gets.
- `evidence.turned` is public now (the fixtures' timed path uses it).
- The fixtures are generated, so they join `.prettierignore` beside `openapi.json`.
**Why:** a test that regenerates the fixtures exactly is worth more than numbers from a model the test can't fit.
**Affects:** T11 and T14 draw from these; T15 regenerates them if planting changes again.

## T10 — Level icons and locked states (2026-10-27)

**Plan said:** `Shared/LevelIcon` beside every level word (Matches, Report, the map and its card, list and dialog,
Feedback); a locked state, "Unlocks after {prerequisite}", dashed, with no icon, on the map and in level rows; the
team-sheet gate copy uses Solid and Sharp.
**We did:** as planned, with these additions:
- **`Shared/LevelWord`** wraps the icon: it takes the level word, band, mastered flag and `waits_for`, and draws either
  the icon with the word or the locked line. Every screen uses it, so the locked state is written once. The map's
  nodes get a fourth state, `locked` (a dashed ring in the asked-now colour), with its own legend entry.
- **The API carries what each row needs.** `Movement` (feedback and the full-time summary) now has `level`, `band`
  and `mastered`; `Bar` (status) and `ConceptMoveOut` (reports) have `waits_for`, computed by the same
  `curriculum.waits_for` the map and the before-match rows use. The browser still computes no level: it only
  compares a mastery to the mastery threshold it is sent, as the map already did.
- **Locked rows keep their number.** A locked row in the report shows "Unlocks after …" in place of the level word
  and keeps the percentage and bar beside it, so the viewer can still see it moving.
- **Captured fixtures refreshed now, not in T15.** The data fixtures (`curriculum`, `concept-map`, `matches*`,
  `report-*`, `sheet-stage-*`) were re-captured from the running API with the saved threat model
  (`tmp/capture_fixtures.py`), since the tests for this task need the eight concepts and `waits_for`. The three
  hand-tuned question/feedback pairs were left as they are, with the new `level`, `band` and `mastered` fields added
  by script; T15 decides whether to re-record them.
- Tests that read the old fixtures were updated to the new values (the in-progress clock, 8 answers with 3 right,
  Chances no longer coming later); the "coming later" and "Not yet" cases are now exercised with a report whose
  Chances strand is emptied by hand, since no live strand is empty any more.
**Why:** one component for the level word keeps the icon rule ("never colour alone") from drifting between screens;
sending `waits_for` on every row keeps the lock rule on the server.
**Affects:** T13's level rows use `LevelWord` as is; T15 only re-records the question/feedback pairs if it wants to.

## T11 — The scene system (2026-10-27)

**Plan said:** `Shared/Scene` with a base layer and the Getting there, Solid and Sharp layers; labels as templates over
the fixture's evidence fields; a 5 s CSS-keyframe loop; Pause motion with `animation-play-state`; a still frame for
reduced motion; specs for the five current concepts.
**We did:** as planned, with these choices:
- **Specs are small programs over the fixture, not drawings.** A spec (`frontend/src/scenes/<key>.ts`) returns a list
  of items per level (`wall`, `line`, `zone`, `label`, `word`, `bracket`, `badge`, `pill`, `flag`, `card`, `ghost`,
  `halo`, `grid`, `move`) in picture metres, placed from the fixture's real players, path and facts; every text is a
  template such as `GAP {gap_m} m`, and `{RESTART_TYPE}` fills in capitals. The boards' layouts were hand-placed for
  invented moments; the fixtures are real ones, so positions have to come from the data.
- **Keyframes are generated into a `<style>` inside the SVG**, one set per scene instance, since the ball's track and
  each label's beat come from the fixture. They are still plain CSS keyframes, so Pause is one class on the root and
  nothing runs on a timer. Beats come from the touches' times, with waits longer than 3 s shortened (a corner taken
  27 s after the ball went out is shown as 3 s).
- **The view is 5 : 4 and at least 50 × 40 m**, centred on the play and the players in it, and grows when the play is
  longer (the Sharp counter-press bracket to goal), rather than cropping to a fixed 50 × 40 that could miss the play.
- **Reduced motion is read in JavaScript** (`matchMedia`), so the still frame is rendered as such: no `<style>`, no
  pause button, the ball and the movers at the start or end position. The CSS media query alone could not move the
  ball to the end frame.
- **Drawing choices the handoff left open:** the defending lines for Line-breaking passes are read off the key frame
  (players within 6 m of each other along the pitch form a line); the pressers in Counter-pressing are the counted
  number of players nearest where the ball was lost, closing in from 5 m further out; the restart taker is the player
  who took it, if within 25 m of the spot. None of these shows a number the pack does not have.
- **Scene text is capped at 40 characters** (a test): on-pitch text is 1.9 units, so longer sentences from the pack
  (such as `booking_note`) belong in the step's paragraph, not the scene.
- The specs test checks the five drawn concepts; T14 adds the three new ones and makes it every fixture.
**Why:** real moments need positions computed from data; generated keyframes keep the no-timer rule.
**Affects:** T12 and T13 render `Scene` inside the step layout; T14 adds specs for Tackles, Shots and Transitions.

## T12 — The step layout and the Welcome (2026-10-27)

**Plan said:** `Shared/StoryStep` (header with Skip, flow label and counter, scene with tag, strand · concept, title,
learner line, paragraph, example card, Back/Next); the Welcome as a step per strand with an active concept, then a
summary; counts from the API; rows grouped by strand at eight or more.
**We did:** as planned, with these choices:
- **`StoryStep` is the frame** (counter, segments, Skip, the scene slot, eyebrow, title, Back/Next) and two small
  cards sit beside it: `SceneCard` (a concept's scene at a level with its tag, or a dashed "Scene coming" card when the
  concept has no spec yet) and `ExampleCard`. The flows in T13 reuse all three.
- **Example prompts are real.** Each step's "You might get" is the scene fixture's level-1 question, worded by the
  template Tutor, rather than the boards' invented prompts (which named clubs that aren't in the league). The copy in
  `frontend/src/scenes/copy.ts` keeps a fallback prompt per concept and level.
- **Strand order.** The welcome tells Game flow first, then Possession, Pressure and Chances (the boards' order), and
  any other strand after in the map's order; the summary rows follow the same order.
- **Chances is a step now**, since Shots and goals is active: its copy is new (the boards had Chances as "Coming
  later") and its scene card is the dashed placeholder until T14 adds the Shots scene.
- **A viewer sent back with an error lands on the summary**, with the reason and Continue, since they have seen the
  steps; a welcome that has no curriculum yet is the summary alone.
- The old "For now they cover N things" line is gone with the old screen; the count now shows as the steps and rows.
- **Headless Chrome here enforces a 500 px minimum viewport**, so T15's phone screenshots frame the page in an iframe
  at 390 px inside a wider host page (`tmp/frame.html`); the Milestone 4 screenshots were taken with an older Chrome.
**Why:** real prompts cost nothing and never name a club that doesn't exist.
**Affects:** T13 builds First look and Level-up from the same three parts; T14 fills the Chances card.

## T13 — First look and Level-up (2026-10-27)

**Plan said:** new screen kinds with `then`; `onWatch` fetches before-match and runs First look, then Level-up, then
Who's playing, skipping an empty flow; a two-level jump gets one step; the last steps carry the level list ("new"
marks), the unlock note, "See your full map" and "On to Who's playing"; `matchHeader` and `offersMap` cover the new
kinds; tests follow the halftime precedent.
**We did:** as planned, with these choices:
- **One screen kind, `before`, with a `flow`** (`first_look` or `level_up`) instead of two kinds with `then`: the
  payload holds both flows, so finishing a First look either re-dispatches the same payload as a Level-up or loads
  the team sheet. `BeforeMatch` is one component for both flows, keyed by flow so each starts at its first step.
- **The First look is marked introduced when its last step is left**, with the result ignored: a failed mark only
  means the First look shows again next time, which is the right failure.
- **The learner line** is `{before}% → {after}% Now {level}` with the level icon; a First look shows
  "Everyone starts at Getting there" with the Getting there icon and no numbers. Mastery on the level list is read
  out to screen readers as a percentage, as the boards' hidden text did.
- **Summary copy** comes from the flow: "That's all three." / "That's the new one." for First looks;
  "Ready for match N." with "One thing moves up to Solid…" or "…to Sharp…" when every move reached the same level,
  else "Two things move up a level." The unlock note shows only when the API sends one (the boards' "Reach Solid…"
  hint for a First look is the team sheet's own gate line, already on Who's playing).
- **Captured fixtures:** `before-match-level-up.json` (the Ripon fan before match 2: Line-breaking passes to Solid)
  and `before-match-first-look.json` (a viewer from before this milestone: three First looks), written by
  `tmp/capture_before_match.py` from the running API.
- Concepts without copy yet (the three new ones, until T14) fall back to the concept's name as the title, a plain
  sentence as the body, and the fixture's question as the example.
**Why:** one screen kind keeps the reducer and `matchHeader` small, and the flow order lives in one place.
**Affects:** T14 adds copy and scenes for the three new concepts, which the First look then shows in full.

## T14 — Scenes for the three new concepts (2026-10-27)

**Plan said:** specs and copy for each level, and an example prompt per level; the Chances card on the welcome swaps
"Coming later" for the Shots scene.
**We did:** as planned. The specs (`tackles.ts`, `shots_and_goals.ts`, `transitions.ts`) follow the catalogue's
"simple pitch scene" shape, from the fixtures' real moments:
- **Tackles and turnovers:** the winner steps in, a ring where it was won and the word for how (`{RECOVERY_TYPE}`);
  Solid names the thirds and shades the one it was won in, with metres from own goal; Sharp shades the ground still
  to cover and gives the high-recovery counts.
- **Shots and goals:** the chance and the shot, then the outcome word; Solid outlines the box it was from and brackets
  the metres to goal; Sharp adds where the chance came from and the shot counts.
- **Transitions and counter-attacks:** the ball won, each receiver running to where they took it, and the box lit when
  the ball arrives; Solid adds a timer to the box and where it was won; Sharp adds the defending line when it was
  won and the shot counts on the break against settled play.
- The copy for the three is new (the boards had none), written from the concept map's objectives and the questions
  each level asks. Example prompts are the fixtures' real questions, as on the other steps.
- The Chances step on the welcome now shows the Shots scene; the dashed card remains for any concept without a spec.
- The specs test now checks every fixture has a spec and copy, and nothing else does.
**Why:** nothing to add.
**Affects:** T15 looks at all eight scenes at three levels in the browser.

## T15 — In the browser (2026-10-27)

**Plan said:** refresh any captured fixtures the planting changed; Lily checks every flow, scene and level in both
themes and with reduced motion; screenshots in `docs/milestone-5/screenshots/`.
**We did:** the captured data fixtures were refreshed in T10 and the before-match ones captured in T13, so nothing was
left to refresh. Every screen was driven in headless Chrome over the DevTools protocol (`tmp/cdp-shot.mjs`: a phone
viewport, clicks by button name, screenshots) against `btl serve --store json` with three viewers set up by script:
`lily` (Ripon fan, match 1 played, a Level-up to Solid before match 2), `old` (a record from before this milestone,
so a First look at the three new concepts) and `hex` (Hexham fan, two matches all right, Level-ups to Sharp and
Mastered before match 3). What that found and fixed:
- **Scene text could leave the view** (a foul near the touchline put "25.9 m outside the penalty area" half off the
  pitch) and **the bottom-right note sat under the Pause button**. Labels and words now shift to stay inside the view,
  and a note along the bottom sits at the left (`edge: 'bottom'`); line labels keep the right edge.
- **A mastered tag** ("Now Mastered") shows the tick, as the level word does.
- The welcome summary's "See all 20 concepts" link was centred by a stale selector; it sits left as designed.
- The "Between the lines" label on the Solid line-breaking scene sat on the defence line; it sits below the
  receiver now.
- Screenshots: the welcome's first step and summary, Matches with locked rows, a Level-up step (dark and light),
  a Sharp step, a Level-up summary with Mastered and New marks, a First look (and its reduced-motion still frame,
  which shows the end of the play), the report and the map with level icons.

**What Lily should check in the browser** (none of this can be read off a screenshot):
1. From `backend/`: `uv run btl serve --store memory --model data/models/expected-threat.json` after
   `npm run build` in `frontend/`, then open http://127.0.0.1:8000 in a private window.
2. The welcome: five steps, each scene looping every 5 s with the labels appearing on their beats; Pause motion
   holds everything mid-loop and Play motion carries on; Back/Next/Skip; the summary's level track and rows.
3. Pick a team, kick off, answer a match through; at Matches the progress rows show icons and the two locked rows.
4. Before match 2, the Level-up for whatever rose (seed-dependent); then Who's playing. Preferences → light theme and
   back, with the scene, tags and icons readable in both.
5. System reduced motion on (macOS: Accessibility → Display → Reduce motion): every scene is a still frame with no
   Pause button; Offside, Fouls and cards, Tackles, Shots and Transitions show the end of the play.
6. A viewer from before this milestone: run `uv run btl learn --viewer NAME` from a checkout of `main` for one
   match with `--learners data/learners`, then `uv run btl serve` (json store) here: "See who's playing" should
   open a First look at Tackles, Shots and Transitions first, once only.
7. The demo on Container Apps is unchanged until this branch is merged and deployed; the learner records there are
   version 3 and will get the First look on their next visit.
**Why:** nothing to add.
**Affects:** nothing.

## T16 — Wrap-up (2026-10-27)

**Plan said:** a summary at the top of these notes; `docs/concept-map.md` with eight active concepts and the new
gating; the `--no-ff` merge into `main` is Lily's.
**We did:** the summary, the concept-map doc (the three new nodes drawn as asked now, the active list, and the
gating paragraph rewritten for `tackles` being active), and the README (a Milestone 5 row in Status, the eight
concepts and the story flows under "Try the web page", five new screenshots, Solid and Sharp in the team-sheet
line, "eight" where it said five). No merge: the branch stops here for review.
**Why:** nothing to add.
**Affects:** nothing.

## After T16 — Re-recording the Tutor's replies (2026-10-27)

**Plan said:** nothing; T5 left the recording to Lily, since it needs the model.
**We did:** re-recorded `tests/fixtures/tutor-replies.json` with `gpt-5.4-nano` (prompt version 5): 144 wordings
over 8 concepts, 178 replies. Two things got in the way:
- **`--record` can't finish in one go.** Of 176 calls, 1 then 5 got no usable reply (transient service errors),
  and `--record` writes only the replies a run got, so each run left holes the tests' `ReplayClient` can't fill.
  A one-off script (not in the repo) replayed what was recorded and asked the model only for the gaps, merging
  the result: 7 more calls, and every request had a reply.
- **The repair prompt wasn't stable.** The Verifier's echo check took a sentence's slots from a set, so when two
  slots echoed in one sentence (`{answer}` and `{chosen}` after a right pick: common for the new "where won"
  question) the failures came out in a hash-dependent order, and the repair request, which lists them, got a
  different key from one process to the next. The replay then missed it in about a third of runs. The check now
  takes the slots in the order they appear; a test holds that order both ways.
- Counts updated: `test_the_recorded_replies_still_pass_as_they_did`, the report line, and the CLI's replay test
  (32 model samples, four per concept).
**Why:** the tests must replay without the model, and a prompt's key has to be the same every time.
**Affects:** the "Checks failed" numbers in `docs/milestone-2b/` are from the old recording; nothing else.

## After T16 — An intro page before the welcome (2026-10-27)
**Plan said:** the welcome (B1) opens straight on the first strand's scene.
**We did:** a still intro page comes first (`Welcome/Intro.tsx`): what Between the Lines is ("from ‘what just
happened?’ to ‘I saw that coming.’"), four lines on how it works (follow a match, answer when play stops, guess first
then see, grow from Getting there to Sharp), then "Show me what I’ll learn" into the scenes or "Skip the tour" to the
summary. It sits outside the step counter, and Back from the first scene returns to it. A viewer sent back with an
error still lands on the summary; Start over lands on the intro.
**Why:** the scenes taught the concepts before anyone was told what the app is or when it asks.
**Affects:** nothing; the App tests click past the intro.

## After T16 — The commentary in the stream view, by surname (2026-10-27)
**Plan said:** the commentary (match clock, "Next question in …", who is on the ball and the spells so far) sits in
the panel, naming players in full.
**We did:** on a wide screen the commentary shows in the stream view, under "Your match: TV, stream or another tab".
It is drawn there through a portal into a slot `App` gives it, so one clock drives both places; the panel keeps its
copy for screen readers only, since the stream view is hidden from them. Below 900 px there is no stream view, so it
stays in the panel. It now names players by surname: each play-by-play touch carries `surname` from the server
(`Player.last_name`) beside the full name, since a surname may have more than one word ("de Wit…") and the
browser can't split it reliably.
**Why:** the commentary follows the match, not the questions beside it, and shorter names read faster.
The team sheet had the same problem: `shirtName` took the last word of the full name, so "de Witkamp" showed as
"Witkamp". Its players now carry `surname` from the server too, and `shirtName` uses it.
**Affects:** the API (`TouchOut.surname`, `SheetPlayerOut.surname`; `openapi.json` and `schema.d.ts` regenerated).

## After T16 — The match feed (2026-10-27)
**Plan said:** nothing; the commentary named who was on the ball and the spells of possession.
**We did:** the stream view now carries the design in `docs/milestone-5/design/MatchFeed-*.dc.html`, standing in
for the viewer's TV between questions.
- **What each player does, and where.** Each play-by-play touch carries `action` ("crosses", "takes the corner",
  "shoots and scores"), `where` ("in midfield", "in the box") and `zone` as a key for the strip of thirds, worded
  on the server (`btl/api/commentary.py`). The zone is seen by the team making the action
  (`learn/play_by_play.zone_of`).
- **The feed.** `learn/match_feed.py` tells the match from kick-off as entries: each passing move (the first of a
  half is the kick-off), goals and own goals with the score after them, shots (saved, wide or deflected for a
  corner, from the action after the shot), corners and throw-ins with their flank, goal kicks, fouls with who was
  fouled and what it gave (free kick, penalty or advantage), cards, offsides, and the halftime break with its
  score. The server words each entry's label and line; the page shows a move once its last touch has happened.
  There are no substitution entries: the simulator makes none.
- **Match stats.** Goals, possession (share of time on the ball), shots, corners, fouls and cards, as a timeline
  of entries from where the viewer left off: one each time the ball changes hands, a number changes or a half
  starts, with the period (`learn/match_stats.py`). The API names shots `attempts`, because the payload leak test
  bars any field called `shots` (an outcome fact for some questions).
- **Nothing past the moment.** The feed and the stats use only events strictly before `names_until`, as the
  spells do. An entry that needs the next action (a shot's end, what a foul gave) says nothing about it when that
  action is at or after the moment. The question's own action is never included: a foul question starts on the
  foul, a restart question on the action before the restart, an offside question on the offside.
- **The page.** On a wide screen the stream view shows the scorebug (crests, codes, You, score, clock and half,
  "Next question in …", possession with home solid and away hatched), the latest action with its strip of
  thirds and "Asked in the panel" at question time, the stats as cards, and the feed, newest first, ending at
  "Start of the match". It replaces the placeholder only between questions; while a question is open the
  placeholder is back. On a phone the panel shows the compact scorebug, the latest action, the note before it
  and "Earlier notes and stats", a sheet with the cards and the whole feed. Teams are a filled disc (home) or a
  ring (away) beside their code, never colour alone.
- **Compression.** A question late in a match carries about 90 kB of JSON, most of it the feed, so the API now
  gzips responses over 1 kB.
- **Left out from the design:** the phone's pitch with player positions (that is the animated playback, still
  to plan), "Adjust timing to match your TV", the "Questions: Normal" pill, the substitution entry, and the
  clubs' colour bars under the scorebug's names.
**Why:** the stream view had room to follow the match, and every word and number in it still comes from the
server.
**Affects:** the API (`TouchOut.action`/`where`/`zone`, `PlayByPlayOut.feed`/`stats`; `openapi.json` and
`schema.d.ts` regenerated). The scorebug shows the score as of the feed, so a goal in the unnamed play before a
saved question shows in the panel's score first.

## After T16 — The welcome fills the window (2026-10-27)
**Plan said:** the welcome sits in the side panel beside the stream view, as every screen does.
**We did:** on a wide screen the welcome (intro page, scenes and summary) fills the window: the stream view and the
panel's resize handle are hidden (`fillsWindow` in `App.support.ts`). Pages of words keep to 640 px; a scene step
widens to 960 px with the scene filling the half beside its words, so the scene is bigger and the page no taller. The intro's four
steps are titles only.
Picking a team keeps the side panel, since Matches and Preferences open it later too.
**Why:** before the first match there is no match to sit beside, so "Your match" was empty space.
**Affects:** nothing.

## After T16 — The question waits for the feed (2026-10-27)
**Plan said:** the step shows the question's heading and its button at once, while the clock runs on.
**We did:** the step reads "The match plays on" until the commentary's clock reaches the moment the question is
asked (`Commentary`'s `onReached`); then the phase pill, the heading, why now and the button appear, and focus moves
to the heading so a screen reader says it. "Skip to the question" gets there at once, so nobody has to wait out the
run (up to 20 s), and the match feed jumps to the moment with it (`atQuestion`), so the two never disagree.
**Why:** the question came before the feed had shown the play it was about.
**Affects:** nothing; tests skip ahead.

## After T16 — How fast the feed plays (2026-10-27)
**Plan said:** nothing.
**We did:** the stream view's header shows how fast the clock plays the match, e.g. "40×" (`playbackSpeed`).
Preferences set it: Feed speed (1×, 20×, 40× or 80×; 1× is real time) and Demo mode (on or off). Demo mode keeps
the old cap, so no wait between questions is longer than 20 s and a long one plays faster to fit; off, every run
plays at the chosen speed. Both are kept in this browser, like the theme, and start at 40× in demo mode, as before.
A change of speed mid-run carries on from where the clock has got to.
**Why:** a viewer couldn't tell the feed runs far faster than a real match, and the 20 s cap is for demos.
**Affects:** nothing.

## After the merge — Small fixes from the screenshots (2026-10-27)
**Plan said:** nothing; these were found in the dark-mode screenshots taken for the video.
**We did:**
- **A count of one takes a singular noun.** The map's wording is written for counts above one, so a pass that broke
  one line read "Breaking one lines". `fill` (`tutor/slots.py`) now makes the noun right after a slot singular when
  the slot's value is "one" or "1", for the nouns the map and templates count (lines, shots, seconds, times,
  recoveries, players, defenders, passes). The map's text and the model's prompts are unchanged, so the recorded
  Tutor replies still match.
**Why:** one rule where slots are filled fixes every such sentence, the model's wording included.
**Affects:** nothing.
- **Scene labels stay in sight.** A zone's value was drawn at the zone's centre, under the players, and the ball (so a
  player) is always in that zone: the Sharp line-breaking scene hid "2.4%" under #2. It is now a small pill on the
  zone's top edge, drawn above the players, or on its bottom edge when the level tag covers the top-left corner.
  A note along the bottom (`edge: 'bottom'`) was still drawn at the right, under Pause motion, although T15 says it
  moved; it now starts at the left.
- **Stat tiles wrap between words.** In the desktop side panel three tiles a row and `overflow-wrap: anywhere` split
  "Bakewell Badgers" into "Bakewe / ll / Badger / s". The row now fits as many tiles as its width allows (at least
  136 px each) and a value breaks only between words, unless one word is wider than its tile.
