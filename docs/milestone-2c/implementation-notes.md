# Milestone 2c: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Engine changes for the web (2026-10-08)
**Plan said:** split the match preparation out of `watch_match` into `prepare_match` so the API layer can cache it; a home flag on each `Marker`; a `reveal_path` that the question view leaves out; the handoff's verdict wording; bump `pack_version`.
**We did:** as planned, with these choices:
- **`prepare_match(course, seed, match_number)`** returns a `PreparedMatch`: the two clubs, the match seed, the match, its context, its phase timeline and its candidates. Nothing in it depends on the viewer's answers. `watch_match` takes an optional `prepare` callable (session seed and match number in, prepared match out). Without it, it prepares the match each time, as before. The answer-time random generator stays in `watch_match`, because questions draw from it as they are asked.
- **`reveal_path` lives on `EvidencePack`,** not on `Picture`. `QuestionView` carries the picture, so a path stored in the picture would reach the browser before the answer. It is the same path an identify question's picture shows (every action of the play, then where the last one ended), now kept for predict questions too.
- **`Marker.home`** says whether the player is on the home club. `side` still says attacking or defending, relative to the ball.
- **Verdicts** are now "Right read." and "Good instinct, not this one.". They are written in `grader.py` only, so the terminal changes too. The README's demo excerpt was updated.
- **`pack_version` is 2.** Every pack id changes; attempts already saved keep their old ids, which nothing reads back.

**Measured** on Lily's Mac, with the default threat model:
- `prepare_match` takes about 0.14 s (the same over 5 seeds).
- Watching seed 7's first match with the demo viewer takes 0.13 s from scratch, and about 4 ms once the prepared match is cached.

**Why:** the plan left these details open. The measurements are for T2's cache decision.
**Affects:**
- **T2:** caches `PreparedMatch` per (session seed, match number) and passes the cached lookup as `prepare`. With it, a request only replays the selector (a few milliseconds), so no further cache is needed. A plain dict is fine: `Course` holds numpy-backed models, so it can't be a cache key, but a server has one `Course`.
- **T6:** draws `reveal_path` on the reveal.
