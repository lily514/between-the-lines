# Milestone 6 implementation notes

## Summary (2026-10-27)
Milestone 6 is finished on `feature/moving-pitch` but **not merged into `main`** for the hackathon: in Lily's browser
check the pitch looked too busy at the default 40× and seemed to stop at times at 1× (T5). The branch is kept, and
pushed when Lily is ready, as the base for a better pace.

**The biggest changes:**
- `learn/track.py` builds the play between two questions as keyframes (players at each action's start, the ball at
  its start and end), stopping on the question's own picture, so it shows nothing of how the play turned out.
- `PlayByPlayOut.track` sends it with every question, seen by the viewer's team, and the leak loops cover it.
- `MatchStep/MovingPitch` draws it in the stream view, following the one match clock; reduced motion jumps keyframe
  to keyframe. The markings, the player glyph and the reduced-motion hook are now shared pieces.

**What was cut (by the MVP decisions):** the phone's pitch, Pause, the real-speed lead-in, the turn into the
question's orientation, and an off switch in Preferences.

**What carries over:**
- **Pace is the open problem.** One speed can't fit both live play and stoppages: gaps of more than 10 s are 7% of
  gaps but 37% of match time (T5). The likely fix is a clock that plays live play near real speed and runs through
  dead time fast, decided on the server from the phase of play (`concepts/phase.py`), so the browser still computes
  no football. The real-speed lead-in is the same idea for the last seconds before a question.
- A whole half's track is 88 kB gzipped; frames could become plain arrays if that matters on a phone (T2).
- The phone's pitch, Pause and the turn are still unbuilt, and nothing in T1–T4 needs redoing to add them.

## T1 — The track (2026-10-27)
**Plan said:** the track covers the actions strictly before `names_until`, its last frame is the question picture,
and the verification checks that no track has a frame at or after its `names_until`.
**We did:** the actions strictly between where the viewer left off and the moment, then one closing keyframe at the
moment itself: the start of the action the question is about (its snapshot, and the ball at its start, without its
flight). That closing frame is the question picture. When the viewer left off at or past the moment, as after a
question saved for a stoppage, or when two questions share one action, the track is empty.
**Why:** a frame at the moment's start is the only way the last frame can be the picture; it shows where everyone
stood as the play began, nothing of how it turned out. The test checks that nothing comes after the moment.
**Affects:** T2's leak checks look for nothing *after* `names_until`; T3 and T4 handle an empty track by showing no
pitch.

## T2 — The track in the API (2026-10-27)
**Plan said:** `TrackOut` has `slots`, `frames` and `ball`; a whole half's track is under 60 kB gzipped.
**We did:** `TrackOut` has `players` (shirt and side, the slots as the page needs them), `frames` (`period`, `at`,
`positions`, `on_ball` as an index into `players`, null when the player isn't tracked) and `ball` (`period`, `at`,
`point`). Over 20 seeds, the largest track (kick-off to the last question of the first half) is 330 kB of JSON,
88 kB gzipped; the budget test allows 400 kB raw. Field names repeat in every frame, which the first estimate left
out. A typical gap of a few minutes is far smaller.
**Why:** the page draws players by shirt and side, as the question picture does; the size is acceptable beside the
feed's 90 kB, and only a first question late in a half carries a whole half.
**Affects:** if the size matters on a phone later, frames can become plain arrays.

## T3 — The moving pitch (2026-10-27)
**Plan said:** draw with the existing `Shared/Pitch` helpers and player styles, without splitting them into shared
pieces.
**We did:** three small extractions, so the moving pitch draws exactly what the question pitch draws without a copy:
`Shared/Pitch/Markings.tsx`, `Shared/Pitch/PlayerMark.tsx` (used by `Pitch`), and `Shared/useReducedMotion.ts` (moved
out of `Shared/Scene`). `besideCarrier` generalises `ballOnScreen`'s offset for a ball that isn't on a picture. The
Pitch and Scene tests pass unchanged. `trackAt` picks the latest keyframe at or before the clock, as `heardAt` picks
the latest touch, so across half-time the pitch and the commentary agree.
**Why:** a second copy of the markings and player glyph would drift; the hook was private to the Scene.
**Affects:** nothing.

## T4 — In the stream view (2026-10-27)
**Plan said:** the moving pitch at the top of the stream view, above the scorebug.
**We did:** as planned, with the pitch's height clamped to 220–440 px (40% of the window between), so the feed list
below it keeps room to scroll. The three captured question fixtures gained a hand-made `track` that fits their
clocks, as their `play_by_play` was written by hand: a keyframe at each touch and a closing frame at `names_until`
with the picture's own players, turned so home attacks up. Not yet seen in a browser; that is T5.
**Why:** a portrait pitch at full column width would push the feed off the screen.
**Affects:** T5 checks the clamp on a short window.

## T5 — In the browser (2026-10-27)
**Plan said:** Lily checks a match from kick-off to full time on a wide screen, with screenshots in
`docs/milestone-6/screenshots/`.
**We did:** Lily checked it. At the default 40× the pitch is too busy to follow; at 1× there are times the game seems
to stop. No screenshots were taken, since the branch isn't going to `main`.
**Why:** the keyframes are uneven. Over seed 7's first three matches the median gap between actions is 2.7 s, but
gaps of more than 10 s (restarts, fouls, goals) are 7% of gaps and 37% of match time, and the longest is 60 s. The
ball's flight is capped at 3 s, so through a long gap it sits still while the players creep to where play restarts.
One speed is too fast for live play or too slow for stoppages.
**Affects:** the branch is not merged for the hackathon; pace is the first thing to fix (see the summary).
