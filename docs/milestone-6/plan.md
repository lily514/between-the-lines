# Milestone 6 Plan: The moving pitch

> Agreed 2026-10-27. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). Milestone 6's branch is `feature/moving-pitch`, from `main` at dd9de93.
> Milestones so far: **1** the data engine, **2a–2e** the learning loop, web page, basics, getting started and AI Tutor, **3** deploy it properly (59b55f4), **4** match day (abfb0c9), **5** more to ask (dd9de93).

## Context

Between two questions the page plays the match as words: the radio commentary in the panel and, on a wide screen, the match feed in the stream view. The pitch only appears once a question is asked, as a freeze-frame. Lily asked for the pitch to move during play: the players and the ball, following the match clock, from where the viewer left off to the next question.

Milestone 5 left this open on purpose: its notes list "the phone's pitch with player positions (that is the animated playback, still to plan)" as left out from the `MatchFeed-PhoneLive` design.

**What the code already settles:**
- Every match stores where each player stood at the start of every action (`Positions.xy` in `schema/snapshot.py`). Nothing new needs simulating.
- `btl replay` already animates play in the terminal (`replay.py`): players move in straight lines between snapshots, and the ball flies from an action's start to its end, its flight capped at `LONGEST_ACTION` (3 s).
- The play-by-play already stops at `names_until`, so it says nothing of how the asked-about play turned out (`learn/play_by_play.py`, `api/payloads.py`). The pitch can follow the same rule.
- One clock drives the step: `Commentary.tsx` runs it with `requestAnimationFrame` and `clockAt`, at the viewer's speed (40× by default, demo mode capping a run at 20 s).
- `Shared/Pitch/index.support.ts` has the drawing helpers (`toScreen`, `MARKINGS`, `viewBoxText`), already shared by the Scene and the kick-off pitch.
- **Size:** about 15 actions a minute, so four minutes of play is about 60 keyframes, 16 kB raw and 5 kB gzipped. A whole half is under 60 kB gzipped. The positions can travel in the step payload; no new endpoint is needed.

**Decided (Lily, 2026-10-27): the smallest version that works.**
- **Which way up:** the viewer's team attacks up for the whole match (home, if they haven't picked a team). When the question comes, the page cuts to the question's own pitch, with no turn.
- **Speed:** one speed throughout, the viewer's chosen feed speed. No real-speed lead-in.
- **After a saved moment:** the pitch holds its last frame until the clock reaches the question.
- **Where:** the stream view on a wide screen only. The phone keeps its text commentary.
- **No off switch** in Preferences, and **no Pause button**: Skip to the question stops the motion (the pitch jumps to its last frame and stays), which is the stop WCAG 2.2.2 asks for, and reduced motion is handled.
- **How it runs:** one commit per task, after Lily reviews the diff.
- **Later, without redoing anything:** the real-speed lead-in, the pitch on a phone, the turn into the question's orientation, Pause, and the off switch.

## How it works

- **The track.** A new pure module, `learn/track.py`, builds the play between two points in the match as keyframes: each action's start time, every player's position at its snapshot, who is on the ball, and the ball's path (at the action's start, then at its end once its capped flight is over). It reuses `replay.py`'s flight rule rather than writing a second one. A period change is a cut, never a glide across half-time.
- **Nothing past the moment.** The track covers exactly the actions the spells cover: strictly before `names_until`. For a live question its last frame is the question picture itself (the same snapshot and ball). A test checks this for every concept, and the new field joins the leak loops in `tests/api/test_payloads.py` and `test_session.py`.
- **Orientation on the server.** Coordinates are flipped with `schema/frames.seen_by` for the viewer's team, into the picture convention, so the page draws them with the same `toScreen` as every other pitch. The browser never decides which way is up.
- **The API.** `PlayByPlayOut` gets a `track`: `slots` (shirt, home or away, in a fixed order), `frames` (match-clock time, one position per slot or null when unknown, and the index on the ball), and `ball` (time, point). Numbers are rounded to 0.1 m. `openapi.json` and `api-types` are regenerated in the same commit.
- **The browser only draws.** `trackAt(track, at)` in a `.support.ts` finds the two keyframes around the clock and blends them linearly, with a gentle ease inside each segment. That is drawing, not football: every position and every time comes from the server. Past the last keyframe it returns the last frame. A player with no known position (sent off, say) isn't drawn.
- **One clock.** The moving pitch takes Commentary's `at`, so the pitch, the NowCard, the feed and the scorebug always agree. Skip to the question jumps the pitch to its last frame.
- **Reduced motion.** No gliding: the players and the ball jump to each keyframe as the clock reaches it, so the picture still follows play, one action at a time.
- **Screen readers.** The SVG is `aria-hidden`; the NowCard and the feed already say what is happening, in words.

## Tasks

| # | Task | Done when |
|---|---|---|
| T0 | Plan | `docs/milestone-6/plan.md`. `CLAUDE.md`: the M6 branch line and a "What this is" line. A README row for Milestone 6 |
| T1 | The track | `learn/track.py` with `Track`, `TrackFrame` and `track_between(match, after, before)`, reusing `replay.py`'s flight cap (made public). Tests: it stops strictly before `before`; a live moment's last frame equals its picture; the ball's flight is capped; a period change is a cut; unknown positions stay unknown |
| T2 | The track in the API | `TrackOut` on `PlayByPlayOut`, built in `api/payloads.py` from the track seen by the viewer's team. The leak loops cover it, for every active concept. A test checks the payload stays under a budget for a late question. `openapi.json` and `api-types` regenerated |
| T3 | The moving pitch | `MatchStep/MovingPitch.tsx` with `trackAt` in `MovingPitch.support.ts`, drawing with the existing `Shared/Pitch` helpers and player styles. Players, ball and a halo on the player on the ball; your team's ring; reduced motion jumps keyframe to keyframe. Tests for `trackAt` (between keyframes, at a cut, past the end, unknown players) and for the component |
| T4 | In the stream view | The moving pitch at the top of the stream view, above the scorebug, with the note "Pitch and feed · follow the match clock". It holds its last frame after a saved moment. While a question is open the stream view's placeholder is back, as now. The phone is unchanged |
| T5 | In the browser | Lily checks a match from kick-off to full time on a wide screen: both themes, reduced motion, Skip, every speed and demo mode, a saved question, and a goal. Screenshots in `docs/milestone-6/screenshots/` |
| T6 | Wrap-up | Summary at the top of the implementation notes; README updated. The `--no-ff` merge into `main` is Lily's |

## Reuse

- **Frames:** `frame_at`, `_flight` and `LONGEST_ACTION` (`replay.py`); `seen_by` (`schema/frames.py`); `Positions` (`schema/snapshot.py`).
- **Where play stops:** `names_until` and `_between` (`learn/play_by_play.py`), and how `api/payloads.py` builds the play-by-play.
- **Drawing:** `toScreen`, `MARKINGS`, `viewBoxText`, `ballOnScreen` (`Shared/Pitch/index.support.ts`), and the player styles in `Shared/Pitch/index.css`.
- **The clock:** `clockAt` and `runMs` (`MatchStep/Commentary.support.ts`, `Commentary.tsx`).
- **Motion:** the motion tokens (`styles/tokens.css`) and the Scene's reduced-motion handling (`Shared/Scene`).

## Out of scope

The items under "Later" above, plus curved runs, a camera that follows the ball or zooms, goal celebrations, substitutions on the pitch, sound, "Adjust timing to match your TV", and the terminal (`btl replay` already covers it).

## Risks and cuts

1. **Straight lines look robotic.** Snapshots are about 4 s apart, so players move in straight legs and the ball can wait at a spot for its receiver. The ease inside each segment helps; curved paths are out of scope.
2. **Busy at high speed.** At 40× the players move fast. Accepted for this milestone; the real-speed lead-in is the fix, later.
3. **Leaks.** The pitch shows more than the words do: positions, not just names. The track must stop where the spells stop for every concept, restarts and shots included, and the leak loops are the gate.
4. **Dead balls.** During a stoppage the players glide from where play stopped to where the restart is taken, and the ball floats to its restart spot. Acceptable, and true to the data; noted if it looks wrong in the browser.
5. **Frame rate.** 22 players re-rendered every frame. Commentary already re-renders every frame; if it stutters, positions are set through refs instead of state.
6. **Payload size.** Bounded by T2's budget test; the API already gzips.

**Cut order if short:** the halo on the player on the ball, then the ease inside each segment (keep linear).

## Verification

- **Each backend task:** from `backend/`, `uv run pytest`, `uv run pytest -m slow`, `uv run ruff check --fix && uv run ruff format`, `uv run pyright`.
- **Each frontend task:** from `frontend/`, `npm test`, `npm run lint`, `npm run build`.
- **No leaks:** the track in every leak loop, and a test over 20 seeds that no track has a frame at or after its `names_until`.
- **Matches the question:** for every live question in seed 7's first three matches, the track's last frame equals the question picture.
- **Size:** the largest track over 20 seeds' matches, reported in the notes.
- **Lily's browser check:** T5.
