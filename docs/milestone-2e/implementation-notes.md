# Milestone 2e: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Your club in the record (2026-10-16)
**Plan said:** `LearnerState.club`, version 2 (loads version 1); `Course.fixture` uses the club's fixtures; `start_session` and a `choose_club` that refuses after the first answer; `btl learn --club`. Without a club, the demo viewer's attempt log over 3 matches is identical to before.
**We did:** as planned, with these choices:
- **`start_session` doesn't take a club.** A new viewer is created first, then `choose_club(course, store, viewer_id, club)` sets it. Choosing needs the league to check the club exists, and `start_session` has no course. Choosing the club the viewer already has is allowed at any time and changes nothing.
- **The club can change while nothing is answered and match 1 isn't finished** (`LearnerState.can_choose_club`). A match with no questions would otherwise let a viewer switch clubs after watching it.
- **A club's fixtures** are its 18 in season order, picked with the same rule as before (`(seed × 7 + match number) mod count`), so its three matches are three different opponents. The match seed is unchanged.
- **Version 1 records** read as having no club and are saved as version 2 the next time they change.
- **The prepared-match cache** is keyed by seed, match number and club; `watch_match`'s `prepare` takes the club as a third argument.
- **`btl learn --club`** takes a name or short code, ignoring case (`League.find_club`), and prints "Your team: …" before each match. The terminal team sheet comes with T2.
- **No change without a club:** `btl demo-viewer` output for seeds 7, 3 and 11 is byte-identical to main's, and a test pins seed 7's three fixtures.

**Why:** the plan left these details open.
**Affects:** T4 (`PUT /api/viewers/{id}/club` maps `ClubLockedError` to 409; `POST /api/viewers` with a club calls `start_session` then `choose_club`).

## T2 — Positions and team sheets (2026-10-17)
**Plan said:** `league/positions.py`; `learn/team_sheet.py` with stages 1 and 2, built from the same `pick_lineup` call the engine makes; the stage from mastery. Tests: every slot has a name; the sheet's players are exactly those in the match, over 40 seeds; stage 2's spots equal the kick-off snapshot.
**We did:** as planned, with these changes:
- **Position names live in `sim/position_names.py`,** not `league/`. They are named from formation slots, which belong to `sim/shape.py`, and `league` sits below `sim`. A slot is wide if it is at either end of a line of four (defence, midfield) or three (attack); right and left are the team's own.
- **The formation is now named once:** `MATCH_FORMATION` (4-4-2) in `learn/candidates.py`. `play_designed_match` passes it to the simulator instead of relying on the default, and `designed_lineups` builds both elevens from it. `PreparedMatch` carries the line-ups. Nothing changes: `btl demo-viewer` output is still byte-identical, and a test checks the line-ups against the players each match tracks, in order, for several pairs of clubs.
- **`team_sheet(match, lineups, match_number, stage, club)`** takes the match and line-ups, not the course and record; the caller works out the stage with `sheet_stage`. Stage 3 shows the same as stage 2 until T3 adds the numbers.
- **Each line is listed left to right as the team faces** (left back first), as the handoff asks. Kick-off spots come from the first action's snapshot, seen with the sheet's first team attacking towards x = 105, so the page can draw your team attacking up.
- **The terminal shows positions without their descriptions.** Twenty-two descriptions would bury the start of the match; the web page shows them.

**Learned:** the back four wears 2 (right back), 3, 4 and 5 (left back), because shirt numbers follow the squad order from the right touchline. Traditionally the left back wears 3. Changing it would move players between slots and so change every match, so it stays.
**Why:** the plan left these details open, and `league` can't import `sim`.
**Affects:** T3 (adds the numbers to `team_sheet`), T4 (the API calls `sheet_stage` and `team_sheet` with the cached `PreparedMatch`).
