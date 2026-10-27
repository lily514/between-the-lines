# Milestone 5 — Implementation notes

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
  fail. Re-recording needs the Foundry model, which this run never calls. **Lily:** from `backend/`, save
  `tests.fixtures.learning.threat_model()` to a file and run
  `uv run btl tutor-eval --model FILE --seeds 1 --per-kind 1 --record tests/fixtures/tutor-replies.json`
  once, after T7, since the new concepts add kinds of question too; then update the counts in
  `test_the_recorded_replies_still_pass_as_they_did` and the report line to what the recording gives.
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
