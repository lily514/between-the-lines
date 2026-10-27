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
