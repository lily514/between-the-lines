# Milestone 2d: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

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
