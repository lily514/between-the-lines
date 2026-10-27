# Milestone 6 implementation notes

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
