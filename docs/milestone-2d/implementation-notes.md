# Milestone 2d: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## Summary (2026-10-16)

Milestone 2d is done, apart from Lily's hand check in the browser. A newcomer now starts on three tier-0 concepts: restarts, offside, and fouls and cards. Restarts and fouls are asked in the stoppage they cause, before the restart is taken. Offside is predicted before the pass in settled play, and reviewed later otherwise. The basics take at most three questions a match, so line-breaking passes and counter-presses still come up from match 1.

**Biggest changes from the plan**
- **Blocks stay unrecorded (T2).** Real event data drops blocks, so about a fifth of throw-ins and nearly half of corners follow the restarting team's own action. Recording a defender's touch, as planned, would have made the simulator less like real data. Instead it now blocks balls out the same way, and the detector works out the last touch from the Laws.
- **When a moment may be asked has three cases, not two (T7):** in play, at the stoppage, and only afterwards (advantage).
- **A question's form depends on the moment (T7):** at the same stoppage, a booking is explained while another foul is predicted.
- **Fouls near the box are graded higher (T7).** A tier-0 concept's prior is already level 2, and plain fouls were too easy to be asked at all.
- **Every live question used to mean settled play;** a live question in a dead ball now has its own wording in the terminal and on the page (T7, T8).

- **The tier-0 prior is 0.35, down from 0.40,** so the basics start on level 1 (see the last note).

**Cut:** nothing from the cut list. A separate foul-spot mark was dropped, because the ball is already drawn there.

**Carries over:**
- Lily's hand check of the page (T8).
- One open point: the misconception after a wrong answer is still picked by the pack's id, not by the mistake.
- For 2b: the Verifier's `grounded` check needs entries for the seven new kinds of question, and the 2b draft plan is updated before 2b starts.

## T1 — Questions per concept (2026-10-16)

**Plan said:** one table per concept in `questions.py`, saying its form, how to build its options, and its quality rule.
**We did:** three tables, each in the module that already owned that piece:
- `QUESTIONS` in `questions.py`: the form and the options;
- `WORTH_TEACHING` in `candidates.py`: the quality rule (only concepts that have one);
- `FACTS` in `evidence.py`: what is known before answering, and what answers.

`ASKABLE` is now the keys of `QUESTIONS`, and a test checks that `FACTS` covers the same concepts.
**Why:** `evidence.py` imports `questions.py`, and `questions.py` imports `candidates.py`. One table holding all three would have to import from all of them and would create a circular import. Keeping each rule beside the code it replaces also keeps the diff small.
**Affects:** T7 adds each new concept to all three tables (two, where it has no quality rule).

The "no behaviour change" check was run by hand rather than as a test, since it compares before and after. The demo viewer's terminal output for seeds 7, 11 and 23 is identical, and so is every evidence pack (as JSON, including `pack_id`) and every attempt for seeds 7, 11, 23, 41 and 99.

## T2 — Who touched it last (2026-10-16)

**Plan said:** record the defender's touch before a corner off a deflection (a `CLEARANCE` by the defending team), add `tackle_out_share`, and test over 200 seeds that every throw-in and corner goes to the team that didn't make the action before it.
**We did:** the opposite on recording. Blocks stay unrecorded, as in real event data, and there are more of them. New `deflected_out_share` (0.05): a pass or dribble the opponent gets to is sometimes blocked out over the nearest line instead, so the team that lost it gets the throw-in, the corner or the goal kick. `tackle_out_share` isn't needed. The test checks that a blocked ball goes out over the nearest line for the same team, and three new calibration bands count the restarts taken by the team that made the action before them (`MatchStats.kept`).
**Why:** the same 40 real matches as Milestone 1's bands, converted with socceraction, show that the plan's rule fails on real data. socceraction drops StatsBomb's `Block` events, so a deflection is usually missing:

| Restart taken by the team that made the action before it | Real | Sim before | Sim now |
|---|---|---|---|
| Throw-ins (of all throw-ins) | 8.2 (of 45) | 0 (of 34) | 7.6 (of 41) |
| Corners (of all corners) | 4.9 (of 11) | 5.5 (of 8.6) | 5.6 (of 9.0) |
| Goal kicks (of all goal kicks) | 0.8 (of 17) | 0 (of 17) | 0.6 (of 17) |

Sim figures are means over the 50 calibration matches.

The most common raw event in between is a `Block` by the other team: about 4.8 a match before those throw-ins, and 4.7 before those corners. The sim's corners already matched real data. Recording a defender touch would have made the sim less like real matches, and a detector that relied on it wouldn't work on them.

Side effects, all towards real football: transition share 59.5% → 57.6% (real 47%), and dead balls 85 → 93 a match (real 103), 56 → 58 of them 15 s or more (real 70). The sample match, the xT grid in [expected-threat.md](../milestone-1/expected-threat.md) and the README's outputs are regenerated.
**Affects:** T4. The restart detector can't read the last touch from the events. By the Laws, the restart goes against the team that touched the ball last, so when the restarting team made the last recorded action, the detector concludes that the ball came off an opponent, and the question says so. Where the ball went out comes from the restart's own position: a blocked action's end point is where it was blocked, inside the pitch.

## T3 — Offside-consistent snapshots (2026-10-16)

**Plan said:** a flagged receiver stands 0.5–4 m beyond the second-last defender; an unflagged one level or behind. Test over 200 seeds that an offside check from the Laws agrees with every flag.
**We did:** as planned, with two details. A flagged receiver also moves across to the pass's line (its end y), since they are running onto it. And the check from the Laws asks, for a flagged pass, that *some* attacker is in an offside position, not necessarily the one the simulator meant: over 200 matches, all 303 flagged passes have one, and all 51,172 completed passes in the opponents' half have an onside receiver. In 20 of the 303, an onside teammate stands nearer the pass's end than the offside receiver. The events don't change at all: only the shape model's stream draws the new offsets.
**Why:** event data doesn't say who a pass was meant for, so the check can't either. A referee flags the player in an offside position who becomes involved, and for a flagged pass that is the offside attacker nearest where the ball went.
**Affects:**
- T5: the offside detector takes a flagged pass's receiver to be the attacker in an offside position nearest the pass's end (for a completed pass, the next action's player).
- A band test changed. `test_natural_settled_line_breaks_are_plentiful_at_levels_two_and_three` asked for at least 8 settled level-2 line-breaks in every one of 40 matches; the lowest is now 7. Its comment's figures were already stale before 2d (level 2: median 17, lowest 10 at the commit before T2, not median 22, lowest 14). T2 lowered them to median 15, lowest 8, and T3 moved only the lowest match. The floor is now 5 and the comment gives today's figures: level 2 median 15 (lowest 7), level 3 median 33 (lowest 22).

## T4 — Restart detector (2026-10-16)

**Plan said:** `concepts/restart.py` with difficulty 0.1 / 0.3 / 0.5 / 0.75, plus 0.15 within 5 m of a corner flag; the concept map split with the evidence fields listed in the plan.
**We did:**
- The detector class is `BallOutOfPlay` (ConceptId `restart`), since `Restart` is already the simulator's name for kinds of restart.
- As T2's note set out, it decides "off an opponent" from the restart: when the team taking it made the last recorded action.
- A corner after the defending team's own recorded action (a clearance behind) had no difficulty in the plan; it gets 0.4, between a plain goal kick and a throw-in off an opponent.
- The near-corner-flag extra applies to throw-ins only. For a corner or a goal kick, event data says where the restart is taken, not where along the goal line the ball crossed.
- Evidence fields, changed so the explanations read as sentences:
  - `restarts`: `out_side` dropped; whose goal line it was is clear from the restart.
  - `offside`: `offside` becomes `offside_call` ("offside" or "onside"); `beyond_or_behind` added; `in_own_half` dropped (the explanation's rule covers it).
  - `fouls_and_cards`: `metres_from_box` becomes `box_position` ("inside the penalty area", "3 m outside it").
- `offside` and `fouls_and_cards` are in the map with `detector: null` until T5 and T6. None of the three is askable until T7, so the learning loop is unchanged.
**Why:** see each point.
**Affects:** T7 fills the renamed fields.

## T5 — Offside detector (2026-10-16)

**Plan said:** tag forward passes into the opponent's half whose receiver is within 5 m of the second-last defender; difficulty from the margin; agree with `Result.OFFSIDE` over 200 seeds.
**We did:** as planned (`OffsidePass`), measured from the offside line (the furthest of the second-last opponent, the ball and halfway), so "behind the ball" and "in their own half" fall out of the same margin. Two additions to the evidence: "line (m)", for the reveal's offside line in T7, and the receiver's "player id". Over 200 matches it calls offside on every flagged pass and on no completed one.
**Why:** a tag's evidence holds numbers only, and the question needs to know who the receiver is. The player id is stored as a float, which is exact for ids this size. `OffsidePass.receiver` and `offside_line` are public, so T7's questions can work out the other attackers' positions the same way.
**Affects:** T7 reads "player id" back as a `PlayerId`.

## T6 — Fouls and cards (2026-10-16)

**Plan said:** split the booking share into a high one for fouls that stop a promising attack and a low one for the rest, keeping 3.3 bookings a match with at least 3 in 4 explained; a `concepts/foul.py` detector.
**We did:** as planned. `booking_share_promising` = 0.4 and `booking_share_other` = 0.05 give 3.3 bookings a match over the 50 calibration matches. The detector (`FoulCommitted`) judges "promising" with `phase.py`, which counts about 9.6 such fouls a match against the simulator's own 6.3. Its transitions run a little longer, and it includes every foul the simulator counts. So about 80% of bookings are explained, and a test checks at least 75% over 40 matches. The rng draws are unchanged, so only which fouls are booked changes; the sample match's events are regenerated.
**Why:** as planned.
**Affects:** nothing.

## T7 — Questions, selector, pack (2026-10-16)

**Plan said:** the question table for the three concepts; `Candidate.asked_at_stoppage`; `TIER0_CAP` and `TIER0_MATCH_CAP`; `reveal_line`; the restart withheld from the view; template wording.
**We did:** all of it, with these changes:
- **`Candidate.asked_when`, not a flag.** There are three cases, not two: in play (live if settled, otherwise reviewed later), at the stoppage (live in the dead ball straight after, or never) and afterwards (only reviewed). The third is advantage: play went on, so there's no stoppage to ask at, and asking live would show the answer as it happens.
- **A question's form depends on the moment.** `ConceptQuestions.form` (and `question_form`) now take the candidate: at the same stoppage, a booking for stopping a promising attack is identified at level 2 and 3, while every other foul is predicted.
- **Restart options are fixed per kind of restart:** the right one, the other team's restart on the same line, and one from the other line. The levels differ by moment (level 3 gets the balls off an opponent), as the detector's difficulty already does.
- **Offside options are three statements:** the true one, its opposite, and the misconception "offside only counts where the attacker is when the ball arrives", which is never true. When the attacker is onside, the true statement gives the actual reason: level or behind the second-last defender, behind the ball, or in their own half. Level 2's "which attacker" is asked live and in reviews.
- **Fouls near the box are graded higher.** A tier-0 concept's prior (0.40) is already level 2, whose band starts at 0.3, so plain fouls at 0.1 were never asked. A foul inside the box or within 20 m of it is now 0.35 (`IN_OR_AROUND_THE_BOX` in `foul.py`): that's where free kick or penalty is a real question.
- **Fact names.** Offside's fact is `attacker`, not `receiver`, because `receiver` is already an answer fact for line-breaking passes. For "which attacker", it is an answer fact here too. The fouls text uses `foul_outcome` and `booking_note` (whole sentences, so the same text works for a penalty, a free kick and advantage) in place of `booked`, `booking_reason` and `advantage`.
- **A review never names a restart its moment led to.** An offside review asked at the offside free kick would otherwise open "Play has stopped for a free kick". The selector drops the restart's name whenever the dead ball's first action is in the moment's span.
- **No separate foul-spot mark.** The ball is already drawn where the foul was. `Picture.mark` is used for a throw-in's out point only; for a corner or goal kick, where the ball crossed isn't known.
- **Tests changed:**
  - the demo-viewer test checks that every concept *asked about* rises, not every active one;
  - the no-transition test allows live questions in the dead ball after a restart or foul;
  - the selector scenarios start the basics mastered, so they still test the two concepts they were written for.

Over ten demo sessions, a match asks 6.8 questions on average (4 to 8). About 2.4 are basics in match 1 and 2.1 in match 3.
**Why:** see each point.
**Affects:**
- T8: `Picture.mark` and `EvidencePack.reveal_line` need to reach the API and the pitch.
- Two open points for Lily:
  - A tier-0 viewer starts on level 2, because the prior equals the level-2 floor, so level-1 basics questions come only after a wrong answer. Lowering the tier-0 prior to 0.35 would start them on level 1.
  - The misconception shown after a wrong answer is picked from the concept's list by the pack's id, as before. So a penalty mix-up can be answered with the advantage misconception.

## T8 — In the browser (2026-10-16)

**Plan said:** the out point, foul spot and offside line on the pitch; the phase pill; API types regenerated; Lily plays two matches by hand.
**We did:**
- `PictureOut.mark` and `FeedbackOut.reveal_line` reach the page. The pitch draws the mark as a ring and the offside line dashed across the pitch, fading in with the reveal. The crop keeps both in view. There's no foul-spot mark: the ball is already drawn there (see T7).
- The match step also needed a third case: a live question in a dead ball. It now says "Play has stopped at …", shows a "Dead ball" pill with no restart, and explains "Play has just stopped, so there is time to call what happens next." Before, every live question claimed settled possession.
- The captured payloads in `src/test-fixtures/` gained `mark` and `reveal_line` (both `null`), as every real payload now has them.
- Lily's hand check is still to do.
**Why:** see each point.
**Affects:** nothing.

## Tier-0 prior (2026-10-16)

**Plan said:** nothing; the tier-0 prior was 0.40 from Milestone 2a.
**We did:** lowered it to 0.35, Lily's choice after T7's open point.
**Why:** 0.40 is exactly level 2's floor, so a newcomer's first basics questions were level 2 (goal kicks, corners, balls off an opponent), and level 1 came only after a wrong answer. At 0.35 a newcomer starts on plain throw-ins and fouls far from the box. Over ten demo sessions, match 1 now asks 3.0 basics questions (the cap) against 2.4 before, and 6.6 questions in all (5 to 8). Line-breaking passes and counter-presses still come up in every match 1.
**Affects:** nothing. The README's demo excerpt and [learner-model.md](../milestone-2a/learner-model.md) show the new prior.
