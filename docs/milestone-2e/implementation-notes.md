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
