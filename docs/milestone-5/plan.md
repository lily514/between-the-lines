# Milestone 5 Plan: More to ask

> Agreed 2026-10-26. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). Milestone 5's branch is `feature/more-to-ask`, from `feature/ux-improvements`.
> Milestones so far: **1** the data engine, **2a–2e** the learning loop, web page, basics, getting started and AI Tutor, **3** deploy it properly (59b55f4), **4** match day (abfb0c9).

## Context

Lily asked for three more concepts to be askable: **Tackles and turnovers**, **Shots and goals**, and **Transitions** (counter-attacks). Claude Design then sent "welcome, level-ups and adding askable concepts" ([design/HANDOFF.md](design/HANDOFF.md), boards B1–B4 in [design/Welcome-redesign.html](design/Welcome-redesign.html)). It adds an animated welcome, First looks and pre-match Level-ups built on a per-concept scene system, and sets the rule that a concept goes live only when both its back-end and front-end checklists are done.

**What the code already settles:**
- The handoff's open item on 40 / 70 cut-offs is already true: `levels.py`, `LEVEL_FLOORS` in `selector.py` and the Tutor's anchor (picked from the question level) all use them.
- A Level-up can be built from the full-time report's before and after (`learn/report.py`).
- First look needs a record of which concepts a viewer has met. Nothing keeps one today.

**Decided (Lily, 2026-10-26):**
- One milestone covering everything.
- Counter-attacks are planted in every match at every level.
- `TIER0_MATCH_CAP` goes from 3 to 5.
- Once Tackles is active, Counter-pressing (through the inactive Pressing) and Transitions wait until Tackles reaches 0.8. Accepted.
- `concept_map.yaml`'s wording stays as written; its match-level evidence fields are computed instead.
- The team-sheet gate copy moves to Solid and Sharp.
- Out of scope: `switch_of_play` and the window concepts.

**Where it lives:**
- **Branch:** `feature/more-to-ask`, from `feature/ux-improvements`. That branch isn't on `main` yet, so merging M5 carries its three commits too; whether to merge it first is Lily's call.
- **Docs:** `docs/milestone-5/` holds this plan, `implementation-notes.md`, `screenshots/`, and `design/` with the handoff and the "Welcome redesign" export, unchanged.
- **Order inside the branch:** the concepts go active (T5–T7) before their scenes exist (T14). That's fine on the branch, because nothing reaches `main` until both checklists are done.

## How it runs (Lily, 2026-10-26)

- **Who runs it:** a Fable agent runs the milestone overnight, unattended, on `feature/more-to-ask`, in the `.claude/worktrees/ux-improvements` worktree.
- **Commits:** it commits each task as soon as that task's checks pass, with no review between commits. This replaces "after Lily reviews" for this milestone.
- **No merge and no push:** it never merges (T16 stops before the merge) and never pushes. Lily does both.
- **No Azure:** it runs no Azure commands, deploys nothing, and leaves the threat model alone (the `uv run btl serve --model …` path from the main checkout is read-only).
- **When a task can't be finished:** it writes the gap in `implementation-notes.md`, commits what passes, and goes on. If a later task depends on it, it stops and reports. It never skips a failing check.
- **Lily's hand checks:** these (T15 and the per-concept browser checks) wait for the morning. The agent takes its own headless screenshots where it can.

## How it works

- **Levels in the flows.** The API sends each concept's band (`getting_there`, `solid`, `sharp`) alongside its `level` word, so the browser never applies cut-offs. "Mastered" is the Sharp band plus a Mastered tag. A Level-up step happens only when the band rises.
- **First look.** `LearnerState` gets `introduced` (concept keys), with `LEARNER_VERSION` 4. A new viewer starts with every active concept introduced, since the welcome covers them. A record written before the field existed reads as the five concepts active before M5, so returning viewers get First looks for exactly the three new ones. Finishing the flow calls `POST …/introduced`.
- **Level-up "shown once".** Like halftime, the page remembers by match number in memory. A reload may show it again, which is harmless.
- **Scenes.** The handoff's `renderScene(svgEl, sceneSpec, level, options)` becomes a React `Shared/Scene` component with `spec`, `level` and `paused` props, which is the repo's pattern (a divergence to note). Each concept's spec and copy live in `frontend/src/scenes/<key>.ts`. A test fails if an active concept has no spec, so the list is never hard-coded and never silently missing.
- **Scene fixtures.** A new `btl scene-fixtures` command writes one JSON per active concept into `frontend/src/scenes/fixtures/`, from a real moment in seed 7's matches: the evidence pack with every `evidence_field` filled, the snapshot at the key frame, and the play's path with timestamps. A backend test fails if the committed fixtures are out of date, as `openapi.json`'s does.
- **Team-sheet gate copy.** "level 2" and "level 3" become "Solid" and "Sharp" (handoff open item).

## The questions

All three new concepts are review questions (identify), asked at a later stoppage and never live. Where the options are statements, one distractor is the concept's misconception from the map.

| Concept | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Tackles and turnovers | **How did {team} win the ball back?** A tackle, an interception, or the keeper gathered it | **Where did they win it?** Own third, midfield, attacking third | **Why does where they won it matter?** The right reason for its third; the distractor is "deep wins are just as useful" |
| Shots and goals | **Was it on target?** Scored, saved, or off target | **Where was the shot from?** Six-yard box, penalty area, outside it | **How did the chance come about?** Cross, pass, dribble or free kick |
| Transitions | **{team} won it in their own half. What next?** Straight for goal, built up slowly, or lost it again | **How long did they take to reach the box?** Ranges, as the counter-press regain question uses | **What made it a counter-attack, not just a fast attack?** The distractor is "any fast attack" |

**Shots can't give their answer away:** the score and catch-up count only goals before the shot; the step doesn't name the restart, since "kickoff" would mean a goal and "goal kick" a miss; the picture marks where the ball ended.

The map's wording stays as written (it is the source of truth). Its match-level fields are computed so far in the match, including `avg_high_recoveries` (both teams' mean).

## Tasks

| # | Task | Done when |
|---|---|---|
| T0 | Plan and design reference | `docs/milestone-5/plan.md`, and `design/` with the handoff and the export. `CLAUDE.md`: the M5 branch line, a "What this is" line, and the design-reference line |
| T1 | Tier-0 cap | `TIER0_MATCH_CAP` 3 → 5 (`learn/selector.py`), with its tests and `docs/concept-map.md` |
| T2 | Ball-win detector | `ConceptId.BALL_WIN` and `concepts/ball_win.py`, reusing `split_possessions` and `changes_hands_in_open_play`. Span: from the losing team's last action to the win. Evidence: how it was won, and metres from its own goal. Difficulty: higher near a third line. Registered in `concepts/registry.py`, `detector: ball_win` in the map, fixtures under 15 events |
| T3 | Shot detector | `ConceptId.SHOT` and `concepts/shot.py`, for `SHOT` and `SHOT_FREEKICK`. Evidence: outcome (a following `KEEPER_SAVE` means saved), zone, and the previous action's type. Difficulty: how near the end point is to a post. Registered, `detector: shot`, tests |
| T4 | Plant counter-attacks | Difficulty in `CounterAttack`: linear from 7 s to the box (0) to 12 s (1). `CounterAttackTemplate` (modelled on `CounterPressTemplate`): 7–8 s at level 1, 9–10 s at level 2, 11–12 s at level 3, then `PlayOn`. In `TEMPLATES` and `MATCH_DESIGN` at every level. A calibration band for counter-attacks a match. Every match's events change, so demo output, pack ids and captured fixtures move. Noted |
| T5 | Tackles questions | New `Asks` values, `QUESTIONS`, `FACTS`, `SHOWN`, and the `ASKING`/`SETTLED_BY` templates. The hard-coded `OUTCOME_NAMES` lists, `ACTIVE` in `tests/fixtures/learning.py`, and the expected concept list. Check how gating Counter-pressing on Tackles affects `test_the_basics_reach_the_viewer…` |
| T6 | Shots questions | As T5, plus the no-giveaway rule (`ASKED_WHEN` `AFTERWARDS`, the score and catch-up before the shot, no restart named, `mark`). A test plays shot questions through the API and checks the score, catch-up and step text |
| T7 | Transitions questions | As T5. Facts: `seconds_to_box`, and `transition_shots`/`settled_shots` so far, from `concepts/phase.py`. `PACK_VERSION` bumped once |
| T8 | Bands, locks, introduced, and the before-match API | `band` and `key` on `Bar`, `MapConceptOut` and `ConceptMoveOut`. `waits_for` (prerequisite names, from `prerequisites_in_force` and the unlock threshold) on `MapConceptOut` and the level rows. `LearnerState.introduced`, `LEARNER_VERSION` 4 and the store's `.get` fallback, plus `POST …/introduced`. `GET /api/viewers/{id}/before-match` returns `first_looks` (active concepts not yet introduced), `level_ups` (from the last full-time report, where the band rose, with before/after % and bands), `levels` (a row per active concept) and `unlock_note` (whether the team-sheet stage rose). `openapi.json` and `api-types` regenerated in the same commit |
| T9 | Scene fixtures | `btl scene-fixtures` (in `cli/`), the committed fixtures for all eight active concepts, a freshness test, and the command in `docs/setup.md` and `CLAUDE.md` |
| T10 | Level icons and locked states | `Shared/LevelIcon`: quarter-filled for Getting there, half for Solid, full for Sharp, a tick for Mastered. Beside every level word: Matches, Report, the curriculum map and its card, the list and dialog, Feedback. A locked state, "Unlocks after {prerequisite}", dashed, with no icon, on the map and in level rows. The team-sheet gate copy uses Solid and Sharp |
| T11 | The scene system | `Shared/Scene`: the base layer (markings for the crop `-5 0 50 40`, players, ball, path, reusing the `Shared/Pitch/index.support.ts` helpers), and the Getting there, Solid and Sharp layers. Labels are templates over the fixture's evidence fields. Motion: a 5 s CSS-keyframe loop with fade in 0–6%, story 6–90%, fade out 90–100%; labels appear on their beat. A Pause motion / Play motion button using `animation-play-state`. Reduced motion shows a still frame: the start frame, or the end frame for Offside and Fouls and cards. The SVG is `aria-hidden`. Specs for the five current concepts, from the scene catalogue |
| T12 | The step layout and the Welcome (B1) | `Shared/StoryStep`: header with Skip, flow label and counter, scene with tag, strand · concept, title, learner line, paragraph, example card, and Back/Next. The Welcome has a step per strand with an active concept, then a summary (strand grid, level track, "See all 20 concepts", Continue → Pick your team). Counts come from the API. Rows are grouped by strand at eight or more. It replaces `Welcome/`'s current screen and updates its tests |
| T13 | First look (B4) and Level-up (B2, B3) | New screen kinds with `then`. `onWatch` fetches before-match and runs First look, then Level-up, then Who's playing; an empty flow is skipped. A two-level jump gets one step. The last steps carry the level list ("new" marks), the unlock note, "See your full map" and "On to Who's playing". `matchHeader` and `offersMap` cover the new kinds. Tests follow the halftime precedent |
| T14 | Scenes for the three new concepts | Specs and copy for each level, and an example prompt per level. The Chances card on the welcome swaps "Coming later" for the Shots scene |
| T15 | In the browser | Any captured fixtures the planting changed are refreshed. Lily checks every flow, scene and level in both themes and with reduced motion, and screenshots go in `docs/milestone-5/screenshots/` |
| T16 | Wrap-up | Summary at the top of the implementation notes, `docs/concept-map.md` (eight active concepts and the new gating). The `--no-ff` merge into `main` is Lily's |

## Reuse

- **Possessions and phase:** `split_possessions`, `changes_hands_in_open_play` (`schema/possession.py`), and `phase_timeline` (`concepts/phase.py`).
- **Questions:** `_labelled`, `REGAIN_EDGES` (`learn/questions.py`).
- **Evidence:** `_Names`, `_span_if_identify`, `_play_path` (`learn/evidence.py`).
- **Planting:** `CounterPressTemplate`, `_pass`, `_nearest`, `PlayOn` (`plant/`, `sim/script.py`).
- **Before and after a match:** `report()` and `_move` (`learn/report.py`), `level_word` (`learn/levels.py`), and `prerequisites_in_force` (`learn/concept_map.py`).
- **Records:** the `asked_in` pattern for a field added later (`learn/learner.py`, `store/base.py`).
- **Pitch drawing:** `toScreen`, `MARKINGS`, `viewBoxText`, `pathData` (`Shared/Pitch/index.support.ts`), as `TeamSheet/KickoffPitch.tsx` reuses them.
- **Screens:** the halftime `then` pattern (`App.support.ts`, `App.tsx`), the path-draw keyframes (`Shared/Pitch/index.css`), and the motion tokens (`styles/tokens.css`).

## Risks and cuts

1. **T4 changes every match.** Planting counter-attacks moves every match's events, so demo output, pack ids and the captured frontend fixtures all change; the band tests are the gate.
2. **Gating.** Once Tackles is active, Counter-pressing and Transitions wait for it; the demo viewer must still meet all eight concepts over three matches.
3. **Shots must not give the answer away** through the score, the catch-up, the restart or the picture.
4. **The scene system is the biggest front-end piece.** Eight concepts × three layers, all from fixtures.

**Cut order if short:** T14's Sharp layers (keep Getting there and Solid), then the Chances scene on the welcome, then the locked state on level rows (keep it on the map).

## Verification

- **Each backend task:** from `backend/`, `uv run pytest`, `uv run pytest -m slow`, `uv run ruff check --fix && uv run ruff format`, `uv run pyright`.
- **Each frontend task:** from `frontend/`, `npm test`, `npm run lint`, `npm run build`.
- **Enough moments:** a counting script over 20 seeds gives candidates a match by concept and level band. A concept that falls short is reported.
- **The demo viewer:** `uv run btl demo-viewer` asks all eight concepts over three matches; the transcript goes in the notes.
- **Leaks:** the new concepts are added to the leak loops in `tests/api/test_payloads.py` and `test_session.py`, plus the shot no-giveaway test.
- **Old records:** a test loads a version-3 record and gets First looks for exactly the three new concepts.
- **Lily's browser check:** Welcome → pick → First look → Level-up → Who's playing on a fresh viewer and on a returning one, with Pause, reduced motion, both themes, and 390 px and desktop widths.
