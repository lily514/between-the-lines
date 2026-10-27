# Between the Lines — handoff: welcome, level-ups and adding askable concepts

Oct 26, 2026 · @Lily Carlson

## Scope

This handoff adds the animated welcome, per-concept first looks and pre-match level-ups, and sets the rules for growing the list of askable concepts. It extends `HANDOFF.md` (§1–17) and changes nothing there unless a section below says so. Tokens, colour roles, fictional clubs, no betting language, colour never the only signal and every number from the API all still apply.

It has two audiences:

- **Back end (Claude Code):** what each new askable concept must ship so the front end can show it (§ Adding an askable concept).
- **Front end:** the screens, the scene system and the motion rules.

Source of truth for concepts is `concept_map.yaml` (version 1). Reference boards are on the Design canvas "Between the Lines — Welcome redesign": `Story` (B1, welcome), `Story-Solid` (B2), `Story-Sharp` (B3) and `Story-Intro` (B4). `Main` (A) is the single-screen direction, not chosen. All numbers on those boards are illustrative.

## Levels, tiers and the active list

A concept's **tier** is fixed; a viewer's **level** in it moves. Animations multiply by concept × level, never by tier.

| Idea | Values | Where it lives | Drives |
| --- | --- | --- | --- |
| Tier | T0 Newcomer, T1 Casual fan, T2 Engaged fan, T3 Analyst | `concept_map.yaml` `tier` | Starting P(known) via `tier_defaults` (35 / 25 / 15 / 5%) |
| Level | Getting there (< 40%), Solid (40–70%), Sharp (≥ 70%) | UI only (HANDOFF §16) | Which anchor and which scene layer the viewer sees |
| Unlock | 0.8 | `learner_models.bkt.thresholds` | When a concept that waits on this one opens |
| Mastery | 0.95 | same | "Mastered" tag; concept moves to spaced review |

Level → anchor: Getting there = `beginner`, Solid = `intermediate`, Sharp = `analyst`. The Tutor's level picker and the screens **must use the same 40 / 70 cut-offs**. An earlier note used 40 / 80; 70 wins unless the owner says otherwise.

**Active means verifiable.** A concept is askable once the code base can find it and check an answer for it. `concept_map.py` does not decide this: the caller passes `active` into `frontier()` and `prerequisites_in_force()`. A non-null `detector` is necessary but not enough. The front end must never hard-code the list. It reads the active concepts, their strands and their state from the API.

Prerequisites are followed through inactive concepts. Today that means every active concept is open from the start, except a concept that waits on another active one: Transitions waits for Restarts ≥ 0.8 if it goes active.

## Screens

Three flows share one step layout. None of them runs during live play.

| Flow | Board | When it runs | One step per | Last step |
| --- | --- | --- | --- | --- |
| Welcome | B1 | First open, replaces `S7-Welcome` | Strand with an active concept, then a summary | Strand grid, level track, "See all 20 concepts", Continue → Pick your team |
| First look | B4 | Before a match, for concepts that became active since the last visit | New concept, at Getting there | Level list, one row per active concept, "On to Who's playing" |
| Level-up | B2, B3 | Before a match, for concepts whose level rose since the last match | Concept that moved up, at its new level | Level list (moved-up rows marked "new"), unlock note, "See your full map", "On to Who's playing" |

**Order on Matches → Kick off:** First look, then Level-up, then Who's playing. Either flow is skipped when it has no steps. A concept that jumped two levels (Getting there → Sharp) gets one step at its new level.

**Step layout (390 px, 420 px panel):**

1. Header: wordmark, map button (not on B1, which is onboarding), Skip.
2. Flow label ("Before match 2") and a mono counter "1 of 4", over one segment per step. Segments are decoration (`aria-hidden`); the counter is the text.
3. Scene, 350 × 280, with a tag top-left (level icon + "Now Solid", "Now Sharp" or "First look") and a Pause motion button bottom-right.
4. Strand · concept label, title (28 px display), learner line, one paragraph (18 px).
5. Example card: "This match, you might get" + a prompt that uses one of the concept's `question_types`.
6. Back (from step 2) and Next / the last step's primary button, 54 px.

**Learner line:** `{before}% → {after}% Now {level}` in `--know`, percentages in mono, both from the BKT state. First look shows "Everyone starts at Getting there" instead.

**Level icons** (never colour alone): Getting there = quarter-filled circle, Solid = half, Sharp = full. Use them everywhere a level word appears.

**Unlock note** comes from the Who's playing stages (HANDOFF §14.3): first Solid → formations and position tags; first Sharp → players' numbers from watched matches.

## Scene system

Each concept has **one base scene and three layers**, not three animations. Build it in `pitch.js` as `renderScene(svgEl, sceneSpec, level, options)`.

- **Base:** pitch markings for the crop, players and ball at the key frame, the ball's path. Same pitch rules as HANDOFF §5: units are metres, home = filled disc, away = ring, ball white, attacking up, non-involved players at 35–55% opacity.
- **Getting there layer:** no numbers. Defenders as shaded walls (`--away` at 16%), one word at most on the pitch ("Offside", "Foul", "Free kick").
- **Solid layer:** named lines, shirt numbers, short mono labels ("Last touch", "Gap 10 m"), one number per scene from the evidence pack.
- **Sharp layer:** analyst overlays: threat grid, offside line with margin, timings, space left behind. Values from the evidence pack in mono.

Every label is a template over `evidence_fields`, for example `GAP {gap_m} m`. A scene never computes a number.

**Crop:** `viewBox="-5 0 50 40"` (50 × 40 m) at 350 × 280 px. On-pitch text is at least 1.9 units (about 13 px). Line labels sit at the right edge.

**Motion:**

| Rule | Value |
| --- | --- |
| Loop | 5 s, infinite: fade in 0–6%, story 6–90%, fade out 90–100% |
| Beats | Labels and markers appear on the beat their event happens (ball crosses the line → marker; pass played → offside verdict) |
| Easing | `ease-in-out` for movement, linear for appearances |
| Pause | A visible Pause motion / Play motion button on every scene, because loops run past 5 s (WCAG 2.2.2) |
| Reduced motion | No loop, no path drawing. Show a still frame. Default is the start frame; for Offside and Fouls and cards show the end frame so the call is visible |
| Step change | Slide in 240 ms `--ease-out`; reduced motion: 120 ms crossfade |
| Accessibility | The scene SVG is `aria-hidden`; the title, paragraph and example carry the meaning |

All animations are CSS keyframes on SVG groups (`transform: translate`, `opacity`, `stroke-dashoffset` with `pathLength="1"`). No JavaScript timers, so Pause is one `animation-play-state` class on the root.

## Scene catalogue

The five concepts askable today each have all three layers on the boards. Labels in braces are the evidence fields that must fill them; anything else on the boards is illustrative.

| Concept | Getting there | Solid | Sharp |
| --- | --- | --- | --- |
| Restarts (T0) | Ball out over the touchline off Westmere; Northbridge player walks to take the throw | Shot deflects off a defender over the goal line: "Last touch", out marker, corner flag, "Corner" (`last_touch_team`, `out_line`, `restart_type`) | Cross blocked by a touch the data missed: "Last in data: cross", "Block · not in data", "→ Corner" |
| Offside (T0) | Defenders as a wall; #9 drifts behind it; zone lights up; assistant referee's flag rises; "Offside" | Second-last defender line drawn; bracket "{margin\_m} m {beyond\_or\_behind}"; "{offside\_call}" | Ghost marker "Level when played"; the run continues; "Onside · play on" (judged at the pass, not on arrival) |
| Fouls and cards (T0) | Trip in midfield, "Foul", ball placed where it happened, players stand back, "Free kick" | Foul just outside the box: "Foul · outside the box", wall steps back, "{foul\_outcome}" (`box_position`) | "Contact" outside the box, "Lands" inside, box line highlighted, "Free kick, not a penalty" |
| Line-breaking passes (T2) | Two shaded walls light up as the pass gets past them; no numbers | Midfield and Defence lines named; gap bracket "Gap {gap\_m} m"; badge 1; receiver "Between the lines" (`lines_broken`) | Threat grid (6 columns × 8.75 m), start and end zones outlined, "{xt\_before}" and "{xt\_after}" in mono, lines and badges 1, 2 |
| Counter-pressing (T2) | Ball lost; three players close in under a shrinking halo; ball won back | Timer pill counting to "Back in {seconds\_to\_regain} s"; "{pressers} pressers" | Bracket "{metres\_from\_goal} m from goal"; shaded "Space behind if it fails" |

The welcome (B1) uses one scene per strand: Game flow = Restarts at Getting there, Possession = Line-breaking at Getting there, Pressure = Counter-pressing at Getting there. Chances shows a dashed "Coming later" card until a Chances concept is active.

**Example prompts** per concept and level are on the boards. Each must match the concept's `question_types`. Counter-pressing is identify only; Restarts is predict only; predict prompts for Line-breaking are live in settled play only.

## Adding an askable concept

A concept goes live only when both lists below are done. Until then it stays "coming later" and counts as a met prerequisite.

**Back end (Claude Code) ships:**

- [ ] A detector in `ConceptId`, named in the concept's `detector`, owned by no other concept.
- [ ] Question generation for each listed `question_type`, with distractors from `misconceptions` where options are statements.
- [ ] An answer check, so the concept is verifiable and can join `active`.
- [ ] Phase gating (HANDOFF §5, §16): moments found in `transition` are queued as review questions, never asked live.
- [ ] Every placeholder in its prompts and anchors filled from `evidence_fields` (the map loader already enforces this).
- [ ] A **scene fixture** for the front end, from a real moment in the sample match: the evidence pack with every `evidence_field` filled; the snapshot (player ids, team, x, y, ball) at the key frame; the event path (who, from, to, out point, timestamps). One fixture per concept is enough; it drives all three layers.
- [ ] The concept added to `active`, and its BKT state returned by the API with the others.

**Front end adds:**

- [ ] A scene spec: crop, which players are involved, and the Getting there, Solid and Sharp layers, each label a template over evidence fields.
- [ ] Copy for each level, paraphrasing that level's anchor; an example prompt per level that uses a listed question type.
- [ ] Strand placement on the welcome, the reports, the radar and the map. A strand's radar value is the mean of its active concepts (HANDOFF §16).
- [ ] A locked state if it waits on another active concept: "Unlocks after {prerequisite}" on the map and in level lists, dashed, with the level icon hidden.

**Copy and layout that must not hard-code the count:** "For now they cover N things", the strand cards' concept lines, the summary step's row list (group rows by strand at eight or more), and the Chances card, which swaps "Coming later" for its scene once a Chances concept is active.

**Scene effort by data requirement:**

| `data_requirements` | Concepts | Scene |
| --- | --- | --- |
| `events` (a moment) | Possession, Tackles and turnovers, Shots and goals, Transitions, Phase of play, Pressing | Simple pitch scene, like Restarts |
| `events` + `snapshot` | Passing, Chance quality, Press triggers, Expected goals | Positioned pitch scene, like Line-breaking passes |
| `window` | Game state, Pressure shifts, Variance, Control vs. chaos | Not a pitch freeze-frame: an animated timeline or chart. Needs its own design pass first |

Expected threat (`events`, T3) can reuse the threat grid, but its Sharp layer should show threat added over a whole possession, so it doesn't repeat the Line-breaking Sharp scene.

## Open items

- [ ] **Transitions:** it has a detector (`counter_attack`). Confirm whether it is in `active`. If so, it needs a scene fixture, three layers and the locked state (waits for Restarts ≥ 0.8). Its questions are always review, never live predict.
- [ ] **Level cut-offs:** confirm 40 / 70 for both the UI and the Tutor's anchor picker.
- [ ] **Team-sheet gate copy** still says "level 2" and "level 3" (HANDOFF §16). Map to Solid and Sharp, or keep as is.
- [ ] **Scene numbers:** 1.2 m, 10 m, 3 s, 11 m and the threat values 0.02 → 0.09 on the boards are illustrative. Replace with fixture values.
- [ ] **First look scope:** B4 shows all five today. In production it shows only concepts new since the viewer's last visit.
- [ ] **Window concepts** need a design pass before any of them goes live.
- [ ] **`switch_of_play`** detector still has no concept (HANDOFF §10).
