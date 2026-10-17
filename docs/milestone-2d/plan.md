# Milestone 2d Plan: The basics

> Agreed 2026-10-16. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). 2d's branch is `feature/the-basics`.
> Milestone 2 now has four parts: **2a** the learning engine in the terminal (done, f80be81), **2c** the web page (done, bad59de), **2d** the basics (this plan), **2b** the AI Tutor (planned). **2d is built before 2b**: none of it needs Azure, and it gives the Tutor three more concepts to word.

## Context

Today the loop asks about two tier-2 concepts, line-breaking passes and counter-presses. A newcomer has nothing at their level. The concept map already has a tier-0 `rules` concept (offside, fouls and set pieces) with no detector, and its own comment says to split it when it's built.

2d makes the bottom of the curriculum askable by splitting `rules` into three tier-0 concepts:

- **Restarts**: who gets the throw-in, and corner or goal kick. Both come from one rule: the team that didn't touch the ball last restarts play.
- **Offside**: would this pass be flagged, and which attacker is offside.
- **Fouls and cards**: after a foul, free kick or penalty, and to whom; why a player was booked; why the referee let play go on (advantage).

The simulator already produces throw-ins, corners, goal kicks, offside flags, fouls, bookings, advantage, free kicks and penalties. Three gaps make them unfit to teach with:

| Gap | Where | Why it matters |
|---|---|---|
| A cross or shot deflected out for a corner records no defender touch | `sim/chain.py` `_cross` (`cross_out_for_corner`) and `_shot` (`miss_out_for_corner`) | The last recorded touch is the attacker's, and the attacker's team gets the corner. The data would contradict the rule we teach |
| An offside flag is a coin flip, and the snapshot doesn't know about it | `_flagged_offside`; `engine._snapshot` places players from the formation only | The picture would often show a flagged receiver onside, and an unflagged one offside |
| A booking is a coin flip (`yellow_card_share`, 13% of every foul) | `_fouled` | Nothing in the play explains a card, so "why was he booked?" would have no true answer |

Also, every throw-in today goes against the team that passed it out: nothing ever knocks the ball out off a defender. That makes "who gets the throw-in" always "the other team", which is too easy past level 1.

Penalty or free kick is already positional and honest: `_free_kick` gives a penalty exactly when the foul is inside the box.

**Not in 2d:**
- red cards and sendings-off: the simulator always plays 11 against 11, and playing with 10 changes the shape model;
- indirect free kicks, handball, the wall and dropped balls;
- the other tier-0 concepts (`possession`, `tackles`, `shots_and_goals`);
- placement for viewers who already know the basics (onboarding, S7);
- new planted moments: restarts, offsides and fouls happen naturally, many times a match.

**Budget:** about 4.75 days, ending around 2026-10-21. Then 2b (about 4 days), Milestone 3 and the video before 2026-10-27. That is tight: if 2d runs long, the cut order below comes first, and fouls and cards as a whole is the last thing cut before 2b's own cuts.

## How it works

**Restarts: asked at the stoppage, as a prediction.**

```
… pass ─► ball goes out ─► [dead ball: QUESTION "What happens now?"] ─► restart ─► …
          key action          picture = snapshot at the key action,        the answer:
          (detector)          path ends where the ball crossed the line    next event's type and team
```

- The question comes while the ball is dead, so it never interrupts a transition.
- It's a **predict** question delivered **live**, but in a dead ball rather than settled play. The answer is the next event, which hasn't happened yet for the viewer.
- It's asked at that stoppage or not at all. A "what restart came next?" asked ten minutes later teaches nothing.
- **No minimum window.** `MIN_QUESTION_WINDOW` (15 s) exists so a *review* question fits in a stoppage. A throw-in's dead ball is 12 s, but the question is about the stoppage itself and is short. The web page steps between moments, so nothing is rushed today. When playing at speed arrives, the page holds the restart until the viewer answers, which changes what is shown, not the match.

**Fouls: the same shape as restarts.**

```
… action ─► FOUL ─► [dead ball: QUESTION] ─► free kick or penalty ─► …
            key action   "What happens now?" (predict)
                         or "#4 was booked. Why?" (identify)
```

- **What happens now** is a live predict at the stoppage, like a restart: free kick or penalty, and to which team. The picture shows where the foul happened and the penalty area, and the answer is the next event.
- **Why was he booked** is an identify question at the same stoppage, about a booking the viewer has just seen.
- **Advantage** has no stoppage at the foul: play goes on. It is a review identify ("The referee let play go on. Why?"), queued and asked at the next long dead ball, as every concept already is.

**Offside: asked before the pass in settled play, or reviewed afterwards.**

- In settled play, a live **predict**: play freezes as the pass is about to be played, and the receiver is named. "Will the flag go up?"
- In a transition, it's queued and asked as a review **identify** at the next long dead ball.
- The detector decides offside **from the snapshot**, never from the event's `Result.OFFSIDE`. It must work unchanged on real data with tracking. T3 makes the snapshot agree with the flag, and a test checks they agree over many seeds.

**Nothing leaks before the answer.** `Timing.restart` names the coming restart ("throw-in", "penalty") and is in the question view today. For restart and foul questions, the view leaves it out, the phase pill says "Dead ball" with no restart, and the 40-seed leak test covers the new concepts.

## Decisions

**Concept map (`learn/concept_map.yaml`).**
- `rules` is split, as its comment planned, into three active tier-0 concepts in strand game_flow:
  - **`restarts`** (detector `restart`): objective "Say which restart comes next, and for which team, when the ball goes out of play."
  - **`offside`** (detector `offside`): objective "Tell whether an attacker is offside when the ball is played to them."
  - **`fouls_and_cards`** (detector `foul`): objective "Say what a foul gives (a free kick or a penalty, and to whom), why a player is booked, and when the referee lets play go on."
- `transitions` now lists `[restarts, tackles]` as prerequisites (it's still inactive).
- Explanation text uses only facts we compute.
- **Misconceptions:** `rules`' three go to `offside`: "Being in an offside position is always an offence", "Offside is judged when the player receives the ball" and "You can be offside from a throw-in". Level-3 offside questions use the last one when the pass is a throw-in. `fouls_and_cards` gets new ones: "Every foul is a booking", "A foul is a penalty if the player lands inside the box" and "The referee should always stop play for a foul".
- Evidence fields:
  - `restarts`: `restart_type`, `restart_team`, `last_touch_team`, `out_line` (touchline / goal line), `out_side` (whose goal line);
  - `offside`: `receiver`, `margin_m` (how far beyond or behind the second-last defender), `offside` (yes/no), `in_own_half`;
  - `fouls_and_cards`: `fouled_team`, `fouler`, `restart_type` (free kick / penalty), `metres_from_box` (negative inside it), `booked` (yes/no), `booking_reason`, `advantage` (yes/no).

**Detectors (`concepts/`, new ConceptIds `RESTART`, `OFFSIDE` and `FOUL`).**
- **`restart.py`**: one tag per throw-in, corner or goal kick. The key action is the last action before it (the one that sent the ball out); the span runs from that action to the restart. Kickoffs, free kicks and penalties are left out. Its docstring defines the rule once: the restart goes to the team that didn't touch the ball last; over the touchline it's a throw-in; over a goal line it's a corner if the defending team touched it last, otherwise a goal kick.
  - **Difficulty:** 0.1 for a plain throw-in against the passer; 0.3 for a goal kick from a missed shot or overhit pass; 0.5 for a throw-in after a defender knocked it out; 0.75 for a corner off a defender; +0.15 when the ball crossed within `NEAR_CORNER` (5 m) of a corner flag, where touchline and goal line are easy to mix up. Capped at 1.
- **`offside.py`**: one tag per forward pass into the opponent's half whose receiver is within `NEAR_LINE` (5 m) of the second-last defender, onside or offside, so the answer isn't always "offside". The receiver is the next event's actor, or for a flagged pass, the attacker nearest the pass's end. Offside position: in the opponent's half, and nearer their goal line than both the ball and the second-last defender, at the moment of the pass (the snapshot). Throw-ins can't be offside.
  - **Difficulty** comes from the margin: 0.1 at 4 m or more either side, rising to 0.9 at under 0.5 m.
- **`foul.py`**: one tag per `FOUL` event. The key action is the foul; the span runs from the fouled team's action before it to the free kick or penalty, or for advantage, to the fouled team's next action. Its docstring defines, once:
  - **Where the foul is judged:** at the ball, where the contact was. It is a penalty if that point is inside the defending team's penalty area, lines included, otherwise a direct free kick. Where the player lands doesn't matter.
  - **Stopping a promising attack** (`PROMISING_ATTACK`): the fouled team is in a transition by `concepts/phase.py`'s definition, and the foul is in the middle or attacking third. This is one of the Laws' reasons for a booking, and the only one the data can show.
  - **Advantage:** the fouled team's next action follows the foul with no stoppage.
  - **Difficulty:** 0.1 for a foul more than `NEAR_BOX` (5 m) from the box; 0.45 for a booking for stopping a promising attack; 0.6 for advantage; 0.6 for a foul within `NEAR_BOX` of the box line, either side; 0.85 within 1 m. The highest that applies.

**Simulator (T2, T3, T6).** All the changes follow M1's rule: events never depend on positions, and positions are drawn to explain the events.
- **Defender touches (T2):**
  - A deflection out for a corner adds one step `by_defence` before the corner (a `CLEARANCE`, `Result.FAIL`; T2 checks socceraction's convention for deflections and notes it).
  - New `tackle_out_share`: a share of tackles and interceptions knock the ball out instead of winning it, for a throw-in (or corner) to the team that had it. Total throw-ins and corners per match stay in their real bands.
  - The extra event must not start a transition in `concepts/phase.py`: the ball goes dead straight after it.
- **Offside-consistent snapshots (T3):** `Step` gains `receiver: int | None`. `engine._snapshot` places the receiver of a forward pass:
  - flagged: 0.5–4 m beyond the second-last defender;
  - not flagged: level with or behind them.
  
  Nobody else moves, so other attackers can still stand offside, as in real play.
- **Bookings with a reason (T6):** `yellow_card_share` splits in two:
  - `booking_share_promising`: high, for a foul that stops an attack in a transition in the middle or attacking third;
  - `booking_share_other`: low, for every other foul.
  
  The simulator uses its own transition flag, which is close to but not the same as `phase.py`'s. Bookings per match stay in the real band (3.3). Questions ask only about bookings the detector can explain, so a booking from the low share that the detector can't explain is simply never asked about.
- **Downstream:** the sample match is regenerated, and the xT grid is refitted and its doc updated, as in 2a's T13. Line-breaking and counter-press candidate rates are rechecked against their bands, since receivers move a little.

**Questions (`learn/questions.py`).** T1 turns the if/elif into a table per concept: each concept says which form it uses for a level and delivery, how to build its options, and its quality rule. `ASKABLE` becomes the table's keys. Three options, one correct, as always.

| Concept | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Restarts (predict) | "What happens now?" Throw-in to each team, plus a goal kick or corner | Same, from harder moments: goal line, both teams' corner and goal kick | Deflections and near-corner moments; options mix type and team |
| Offside, live (predict) | "Will the flag go up?" Yes / No, onside / No, in their own half | "Which attacker would be offside?" Three attackers as pitch targets, exactly one offside (skipped if more than one is) | Tight margins (difficulty ≥ 0.6) |
| Offside, review (identify) | "Was #9 offside when the pass was played?" Three statements, one true, the others misconceptions | As live level 2, asked after the play | Tight margins |
| Fouls, at the stoppage (predict) | "Foul by #4. What happens now?" Free kick to the fouled team / free kick to the other team / a penalty or a throw-in | Near the box: free kick or penalty, and to whom | Within 1 m of the box line |
| Bookings, at the stoppage (identify) | Not asked | "#4 was booked. Why?" Stopping a promising attack / misconceptions as the other two | Same |
| Advantage, review (identify) | Not asked | Not asked | "The referee let play go on after #4's foul. Why?" The fouled team kept the ball, so stopping play would have helped the team that fouled / two misconceptions |

- Offside level 2 reuses the pass options' `target` / `target_at` machinery, so the pitch already knows how to draw it.
- A foul tag gives one question, chosen by the level: a level-2 or 3 question about an explained booking asks why; otherwise it asks what happens now.
- New `Asks`: `WHAT_RESTART`, `FLAG_OR_NOT`, `WHO_IS_OFFSIDE`, `WAS_IT_OFFSIDE`, `AFTER_THE_FOUL`, `WHY_BOOKED`, `WHY_PLAY_ON`.

**Selector (`learn/selector.py`).**
- `Candidate` gains `asked_at_stoppage: bool` (true for restarts, and for fouls that stop play). Such a candidate is offered at the dead ball straight after its key action, with `Delivered(LIVE, …, DEAD_BALL)`. It ignores `MIN_QUESTION_WINDOW`, is never queued, and counts towards `IN_PLAY_CAP` and `SPACING` like any live question.
- **Keeping the existing concepts in view.** Restarts happen about every 90 seconds and fouls every 3.5 minutes, so walking in time order, they'd take almost every slot until mastered. New caps: `TIER0_CAP` = 2 questions per match per tier-0 concept, and `TIER0_MATCH_CAP` = 3 tier-0 questions per match in all. With three concepts, the per-concept cap alone would allow 6, which is the whole match. So line-breaking passes and counter-presses still come up in a beginner's first matches. A test checks this with the demo viewer.

**Evidence pack (`learn/evidence.py`; `pack_version` goes up by one).**
- An outcome function per concept, in T1's table.
- The restart picture: the snapshot at the key action, with the path ending at the point where the ball crossed the line (`where_it_leaves` lives in `sim/pitch.py`; the detector computes its own from the event's end point, since concepts don't import the simulator).
- The foul picture: the snapshot at the foul, with a mark at the foul's spot.
- The offside reveal: a new `reveal_line` (the second-last defender's x), which the question view leaves out, like `reveal_path`.
- Restart and foul questions: `Timing.restart` is `None` in the view.

**Tutor (`tutor/templates.py`).** `ASKING` gets the seven new questions. Feedback uses the map's explanations as before. `tutor/` still imports nothing from sim, value, concepts or plant.

**Frontend.**
- `Pitch` gets three new marks:
  - the out point (a small mark on the line);
  - the foul spot (the same mark, off the line);
  - the reveal's offside line (a dashed line across the pitch, from `--` tokens).
  
  The crop keeps the out point, the foul spot and, for a foul near the box, the penalty area inside the `viewBox`.
- `PhasePill`: "Dead ball" with no restart name when the pack withholds it.
- Regenerate the API types.
- No new screens.

**Note for 2b's draft.** The Verifier's `grounded` check is written per question kind (pass questions use `{answer.*}`, identify questions use `{answer}`). The new asks need entries, and the 40-seed template sweep covers them. The 2b draft is updated once 2d is merged.

## Tasks

| # | Task | Done when |
|---|---|---|
| 0 | Plan, CLAUDE.md | Plan committed; CLAUDE.md updated (below) |
| T1 | Questions per concept | `questions.py`, `candidates.py` and `evidence.py` use a table per concept instead of if/elif. **No behaviour change:** existing tests pass unchanged, and the demo viewer's attempt log over 3 matches is identical before and after |
| T2 | Who touched it last | Deflected corners record the defender's touch; `tackle_out_share` added. A property test over 200 seeds: every throw-in and corner is taken by the team that didn't make the action before it, and every goal kick follows an attacking action. Throw-ins, corners, goal kicks and actions per match stay in their bands; no new transitions from the added touches. Sample match regenerated; xT refitted; notes |
| T3 | Offside-consistent snapshots | `Step.receiver`; `_snapshot` places a forward pass's receiver from its flag. Over 200 seeds, an offside test written straight from the Laws (not the detector) agrees with every flag. Line-breaking and counter-press candidate rates still in their bands |
| T4 | Restart detector | `concepts/restart.py` on hand-built fixtures (< 15 events each): throw-in each way, goal kick, corner off a defender, near the corner flag; difficulty bands; registered; concept map split as above |
| T5 | Offside detector | `concepts/offside.py` on hand-built fixtures: clearly off, clearly on, level, behind the ball, own half, throw-in; over 200 seeds it agrees with `Result.OFFSIDE` on every flagged pass |
| T6 | Fouls and cards | The booking shares split; bookings per match in the real band, and over 200 seeds, at least 3 in 4 bookings are explained by `PROMISING_ATTACK`. `concepts/foul.py` on hand-built fixtures: free kick, penalty, on the box line, just outside it, an explained booking, an unexplained one, advantage; over 200 seeds, its free kick or penalty agrees with the next event every time |
| T7 | Questions, selector, pack | The question table above; stoppage delivery; `TIER0_CAP` and `TIER0_MATCH_CAP`; `reveal_line`; the restart withheld from the view; template wording. Tests: every level builds a fair set over 40 seeds; the leak test covers all three concepts; the demo viewer sees line-breaking or counter-press questions by match 2 |
| T8 ★ | In the browser | Out point, foul spot and offside line on the pitch; phase pill; API types regenerated. Lily plays two matches as a new viewer, in both themes, at phone and desktop width |
| T9 | Wrap-up | README status row and honest limits; `docs/concept-map.md` updated; implementation-notes summary; `--no-ff` merge |

Rough days: T1 0.5, T2 0.5, T3 0.5, T4 0.25, T5 0.5, T6 0.75, T7 1, T8 0.5, T9 0.25, so about 4.75.

## CLAUDE.md changes (commit 0)

- **Git workflow:** M2d "The basics": `feature/the-basics`. 2d is built after 2c and before 2b.
- **What this is:** Milestone 2d adds the basics: restarts, offside, and fouls and cards.
- **Learning design rules:** add "A question about a restart or a foul is asked at its own stoppage or not at all; these are the only live questions asked in a dead ball."

## Risks and cuts

1. **T2 shifts the whole event stream.** Every match changes, so seeded examples in docs and the README change too. That's expected; T2 regenerates them, as 2a's T13 did.
2. **Moving receivers in T3 changes line-breaking detection.** Only forward-pass receivers move, and only up to the line. The band check catches a large shift; if one appears, T3 moves only receivers in the opponent's half.
3. **The basics crowd out everything else.** `TIER0_CAP` and `TIER0_MATCH_CAP` are the guard; the demo-viewer test checks it.
4. **Offside level 2 finds no fair set** (more than one attacker offside, or none near). That moment is skipped, as predict questions already are when no fair options exist.
5. **The simulator's transition and `phase.py`'s disagree**, so fewer bookings are explained than planned. T6's 3-in-4 check catches it; the fix is to raise `booking_share_promising`, not to loosen the detector.
6. **Fouls near the box are rare** (about 1 a match), so level-3 foul questions may seldom come up. That's acceptable: the selector already falls back to the nearest band.

**Cut order if short:**
1. `tackle_out_share` (deflected corners stay; throw-ins stay at level 1 to 2).
2. Advantage questions (the foul detector still tags advantage, but nothing asks about it).
3. Offside level 2's "which attacker" (levels 1 and 3 use Yes/No).
4. Bookings with a reason, and the booking question (foul questions ask only what happens now).
5. The offside line in the reveal (the margin is shown as a stat tile instead).
6. The near-corner-flag difficulty bonus.

## Verification

- From `backend/`: `uv run pytest`, `uv run pytest -m slow`, `ruff check`, `ruff format --check` and `pyright` all pass. From `frontend/`: `npm run lint`, `npm test` and `npm run build` all pass.
- `uv run btl moments --seed 7` lists restart, offside and foul moments, and their ASCII pictures make sense by eye.
- `uv run btl learn --viewer basics-test`: a new viewer gets questions on all three new concepts within their first two matches, and still sees a line-breaking or counter-press question by match 2.
- `uv run btl serve`: the same in the browser. In DevTools, a restart or foul question's response doesn't name the restart.

## After approval

Create `feature/the-basics` from main. Put this plan at `docs/milestone-2d/plan.md` and show it to Lily before committing ("Add Milestone 2d plan"). Then commit CLAUDE.md, then start T1.
