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
