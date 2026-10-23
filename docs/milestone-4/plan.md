# Milestone 4 Plan: Match day

> Agreed 2026-10-23. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). Milestone 4's branch is `feature/match-day`.
> Milestones so far: **1** the data engine, **2a–2e** the learning loop, web page, basics, getting started and AI Tutor (2b merged at 41d8e5d), **3** deploy it properly (59b55f4).

## Context

Claude Design sent a new handoff ([design/HANDOFF.md](design/HANDOFF.md) §16–17, boards in [design/](design/)). The updated CM-A curriculum map board isn't exported yet; T7 needs it. It turns the app from "one long run of three matches" into a **companion with a home base**:
- First open: Welcome → Pick your team → **Matches** → Who's playing → Kick off.
- Return visits and "Done for this match" land on Matches.
- A **map button** in every header opens the curriculum map from anywhere.
- **Halftime and full-time scouting reports** with a radar.
- **Preferences.**

Today there is no router. A reducer in `frontend/src/components/App.support.ts` shows one screen at a time:
- **Missing:** Matches, map, radar, halftime report and Preferences.
- **Full time** is a simple stand-in.
- **Concept map:** the API never sends it (only `StatusOut.concepts` bars), and sends no level words.

**Decided (Lily, 2026-10-23):**
- **Flow and views; matches still step** from moment to moment (`MatchStep`). The TV-synced live clock is a carry-over. That covers kick-off times as a clock, rejoining at the live minute, the ±10 s sync, and "Save for the break" with the saved chip.
- **It's called Milestone 4,** because Milestone 2 is wrapped up and Milestone 3 (deploy) merged as 59b55f4.
- **The app gets CM-A "Your pitch" as its curriculum map.** CM-C (the tree) goes in the docs and README.
- **The flow board's three rules are accepted:**
  1. One question per stoppage: the live basics question wins.
  2. A catch-up caption, "While you were answering: …", after feedback.
  3. No live question in the last 30 s before halftime or full time; it becomes a report replay.

**Repo wins over the handoff** (as in 2c/2e):
- The pitch mapping, club names (the crest clubs, not Northbridge/Westmere) and line-breaking definition stay as they are.
- Mock numbers are illustrative only.

**Not in Milestone 4:**
- the live wall clock and TV sync;
- Save for the break and the saved chip;
- S5 three levels with Simpler/Deeper;
- S7 placement;
- player focus, language and haptics in Preferences;
- the CM-B and CM-C screens.

## Step 0, before the branch (needs Lily's OK)

Land 5f88adb "Put both teams on one kick-off pitch…" on `main`. Cherry-pick it as a standalone polish commit, the way a0f12fb went, then retire the `team-sheet-field` worktree. `feature/match-day` then branches from `main`, which includes M3.

## How it works

- **Matches are the viewer's three fixtures, each with a state** (`upcoming` / `in_progress` / `finished`) taken from `LearnerState.match_number` and the attempts, never from the wall clock.
- **Dates:** each match's "Matchday N · Sat 24 Oct · 15:00" comes from a fixed synthetic calendar in `league/` (weekly Saturdays from a season start constant, numbered by the viewer's match).
- **Earlier reports are recomputed on request.** The server rebuilds them from the attempt log with `prepare_match(seed, n, club)`, so the attempt log stays the source of truth and nothing new is stored.
- **Level words come from the server:** Getting there below 40%, Solid 40–70%, Sharp 70% and up, Mastered at 95%. These match `LEVEL_FLOORS` in `learn/selector.py`, so the browser computes nothing.
- **Radar:** each strand's value is the mean P(known) of its askable concepts. Chances has none, so it is `null`: a dashed axis labelled "Not yet", never drawn as zero. The report sends a kick-off value and a now value per strand.
- **The halftime report** is shown when a step crosses period 1 → 2. The step payload already carries the from/to period, so no server state is needed. It is fetched as `GET …/matches/{n}/report?at=halftime`, and break questions are asked before it, as today.
- **The map and Preferences are overlays** on top of the current screen. Closing one returns to the same screen and scroll position. Because matches step, an open question simply waits underneath; it doesn't need to be "saved" (implementation note).

## Tasks

| # | Task | Done when |
|---|---|---|
| 0 | Plan, CLAUDE.md, design reference | Plan committed. `docs/milestone-4/design/` holds the two exports plus HANDOFF.md §16–17. CLAUDE.md: git line (M4 "Match day": `feature/match-day`), "What this is" line, design-reference line |
| T1 | Matches and calendar | `league/calendar.py` (matchday → date and kick-off). `learn/matches.py` gives each viewer match its state, plus score and question count when finished. `GET /api/viewers/{id}/matches`. Tests: no score or count for unfinished matches; dates are deterministic |
| T2 | Curriculum map and level words | `GET /api/concept-map`: all 20 concepts with tier, strand, prerequisites, askable / coming later, and the viewer's value and level word. `level` word added to `StatusOut.concepts`. Settle whether the askable set is 5 or 6 (`transitions` via `counter_attack`) and note it. Tests over the YAML |
| T3 | Reports | `learn/report.py`: radar (kick-off vs now, `null` strand), in progress/mastered, scout's note from concept-map anchors (no invented numbers), up to 2 replay cards, and at full time the goal timeline and recap. `GET /api/viewers/{id}/matches/{n}/report?at=halftime\|full_time`; `FullTimeOut` points to it. Tests include a leak check: a halftime report holds nothing from the second half |
| T4 | Three asking rules | In the selector: one question per stoppage (the live basics question wins and the review waits); no live question in the last 30 s of a half (it becomes a replay); the step after feedback carries a "While you were answering" summary. Demo-viewer bands still pass; the attempt-log change is noted |
| T5 | Navigation shell | `Shared/Header` (title, map button, ⚙). An overlay layer in the reducer for map and preferences, restoring scroll. New screens `matches` and `report`. Flow rewired: first open Welcome → Pick → Matches; return visits and "Done for this match" → Matches. Rebuild Welcome to S7 (five askable concepts by strand). Reducer and keyboard tests |
| T6 | Matches screen (S0) | Next match + "See who's playing"; in-progress card with "Rejoin"; Your progress (five concepts, level words, "See your full map"); Earlier (report links). Phone and side panel |
| T7 | Curriculum map (CM-A) | Pitch layout by strand and tier; "coming later" dashed; level words; prerequisite arrows; a list fallback for screen readers. Opens from every header and from "See your full map" |
| T8 | Scouting reports (S6) | `Shared/Radar` (4 axes, dashed kick-off, solid now, "Not yet" axis, hidden table). Halftime and full-time screens replace `FullTime/`. Desktop halftime takes the whole window |
| T9 | Preferences (S8) | Questions off / rarely / normal (stored in the learner record, applied as selector caps); explanation level Auto/Newcomer/Fan/Analyst (overrides the feedback level); theme system/dark/light (browser only, `data-theme`); "Your team · Change" (existing 409 rule) |
| T10 ★ | Hand check and wrap-up | Lily plays a new viewer end to end in both themes, at phone and desktop width. README "Try the web page" with new screenshots; CM-C tree in the docs; notes summary; `--no-ff` merge. Redeploy only with Lily's go-ahead |

Rough days: T1 0.5, T2 0.25, T3 0.75, T4 0.5, T5 0.5, T6 0.5, T7 0.5, T8 0.5, T9 0.5, T10 0.25, so about 4.75. **That runs past 2026-10-27, so the cut order below matters.**

## Risks and cuts

1. **T4 changes which moments are asked.** The demo viewer's attempt log won't be byte-identical; the band tests are the gate.
2. **Preferences touch the selector.** "Questions off" must still let the match finish and show the reports.
3. **The Tutor:** report and map text is template-only (not model-worded), so the Verifier isn't involved.
4. **Deploy:** new routes need no new Azure resources; Blob learner records gain optional fields (version bump, older files still load).

**Cut order if short:**
1. Preferences except theme and "Your team".
2. The halftime report (keep full time).
3. Earlier reports on Matches.
4. CM-A's prerequisite arrows (keep the strand × tier grid).
5. Rule 2, the catch-up caption.

## Verification

- Backend: `uv run pytest`, `uv run ruff check`, `uv run pyright`.
- Frontend: `npm test`, `npm run lint`, `npm run build`, `npm run api-types` (clean diff).
- **End to end** with `btl serve` and a temporary learners folder:
  1. A new name goes Welcome → Pick → Matches → Who's playing → a whole match → full-time report → Matches.
  2. "Done for this match" mid-match, then "Rejoin" resumes at the same question.
  3. The map opens from every header and closes back to the same screen and scroll position.
  4. The halftime report appears once per match.
- Check that no report or matches response holds anything from a moment not yet reached.
- Screenshots in both themes at 390 px and in the side panel.
