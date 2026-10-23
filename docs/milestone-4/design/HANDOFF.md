# Between the Lines — front-end handoff, §16–17

Claude Design's addenda for Milestone 4. Sections 1–13 are in `../../milestone-2c/design/HANDOFF.md`; §14–15 (club
picker, team sheet, crests) are in `../../milestone-2e/design/HANDOFF.md`. The boards here are reference markup, not
production code: they load `./support.js` (not committed) and use template holes, as before. The repo decides
behaviour and data.

Boards in this folder: `FLOW-Overview` (user flow), `S0-MatchHome`, `S1-Live`, `S1-DeadBall`, `S6-Halftime`,
`S6-Fulltime`, `S7-Welcome`, `S8-Preferences`. Not yet exported: the updated `CM-A-Pitch` curriculum map.

## 16. Addendum: curriculum update (milestone 2d)

Source: Lily's design-update brief for milestone 2d. Everything above still applies (tokens, colour roles, fictional clubs, no betting language, colour never the only signal, every number from the API) unless this section changes it.

### Curriculum
- 20 concepts, 4 tiers, 4 strands. "Key rules" is now three T0 concepts: **Restarts**, **Offside**, **Fouls and cards**. Transitions now needs Restarts + Tackles.
- **Askable now (5):** Restarts, Offside, Fouls and cards (Game flow), Line-breaking passes (Possession), Counter-pressing (Pressure). No Chances concept is askable. Everything else is "coming later" and, as a prerequisite, counts as met.
- **Only the curriculum map shows all 20** (CM-A/B/C), with "coming later" drawn dashed. Reports, Welcome and Full time show only the five askable concepts.
- Starting values by tier: T0 35%, T1 25%, T2 15%, T3 5%. No placement check: `S7-Placement` / `S7-Result` are future work, and "Redo the starting check" is removed from Preferences.

### Levels
- Level is separate from tier. Below 40% = **Getting there**, 40–70% = **Solid**, 70% and up = **Sharp**. In the UI, levels are **always words, never numbers**. Unlock 80% and mastery 95% ticks are unchanged.
- Progress bars carry ticks at 40 and 70 (level steps) and a dashed tick at 95 (mastered).
- Learner sentence after a reveal: `"{Concept}: {before}% → {after}%. Now {level}."` or `"Still {level}."` (e.g. "Restarts: 35% → 62%. Now solid.").
- Known inconsistency, kept on purpose for now: the team-sheet gate copy still says "level 2".

### Asking
- About 6–7 questions a match. Basics are rationed: at most 2 per basics concept and 3 basics in total per match.
- Dead-ball live question: the phase pill reads **"Dead ball · What happens now?"** (action colour, 4 s), like "Your read?" in open play. Options are the right restart, the other team's restart on that line, and one from the other line. If play restarts first, it's saved for the break.
- Prompts per concept (Restarts, Offside live/review, Fouls at the stoppage, Line-breaking, Counter-pressing after the play) follow Lily's brief §3. Wrong offside answers name the reason (level with the second-last defender, behind the ball, or in their own half).

### Scouting report radar
- Strand value = mean P(known) of its **askable** concepts. Game flow covers the three basics; Possession and Pressure each show a small "1 concept" note.
- A strand with no askable concepts (Chances) gets a dashed axis, the label "Not yet", and no point; the shape closes across it. Never draw it as zero.

### New and changed boards
| Board | What |
|---|---|
| `S1-DeadBall` | Live companion at 38:06 with the "Dead ball · What happens now?" prompt |
| `S2-DeadBall` | Live Restarts question (Getting there): "The ball has gone over the touchline, last touched by Westmere. What happens now?" |
| `S4-RestartReveal` | Reveal marks where it went out and the last touch; "Restarts: 35% → 62%. Now solid." |
| `S4-OffsideReveal` | Asked at Solid: "Which of these attackers is in an offside position?", wrong answer, offside line drawn, reason named. **Illustrative positions** |
| `S5-Basics` | Restarts at Getting there / Solid / Sharp (throw-in, goal line, off a defender) |
| `S6-Halftime`, `S6-Fulltime`, `D-Halftime` | New radar rules; "What you're being asked" grouped by strand with level words |
| `S7-Welcome` | Rebuilt: what the questions cover, grouped by strand; everyone starts at Getting there |
| `CM-A`, `CM-B`, `CM-C` | 20 concepts, asked now vs coming later, level words, new prerequisite arrows |
| `Components` | Dead-ball prompt pill; radar empty-strand state |

### Data notes
- The 38:08 throw-in is real: action 646 (Westmere #13 pass from (64.8, 1.0), out at (95.1, 68.0)), then action 647, a Northbridge throw-in. With Northbridge attacking up, the out point is the left touchline at Y 95.1. Player positions on these boards are placed by hand; pull them from `positions.parquet` at the out frame.
- Game 7 has no offside or foul events, so Fouls and cards stays at 35% and is never asked in match 1. The offside reveal and the Solid/Sharp restart examples are illustrative.
- The sample viewer's match 1 (7 questions, 2 basics): 27:40 Offside right 35→52 · 34:18 Line-breaking miss 15→13 · 38:08 Restarts right 35→62 · HT Counter-pressing 15→48 · 58:13 Line-breaking right 13→74 · FT Counter-pressing 48→71 · FT Line-breaking right 74→96 (mastered). These are design values; the real ones come from the API.

## 17. Addendum: end-to-end flow (companion to a stream)

Design files: `design/FLOW-Overview` (canvas page "User flow") and `design/S0-MatchHome` (State tweak: upcoming / live / finished).

- **The app is a companion to a separate stream.** The match never pauses for a question; copy keeps "the match carries on, on your TV". The app follows the match clock.
- **Sync:** "In step with your TV?" with −10 s / +10 s buttons (offset shown in mono, announced politely). It sits on the live Matches card; tapping the clock in the live header opens the same control.
- **Matches is home base.** First open: Welcome → Pick your team → Matches → Who's playing → Kick off. Return visits and "Done for this match" land on Matches. It shows the next match (date and kick-off from the fixture data), a live match to rejoin (clock, score, saved-question count), the five askable concepts with level words, "See your full map", and earlier reports.
- **Map links:** "See your full map" on the halftime, full-time and desktop halftime reports and on Matches. The map's back button is plain "Back".
- **Rules proposed, waiting for the owner to confirm:**
  1. One question per stoppage: the live basics question wins; a saved review waits for the next long stoppage or halftime.
  2. After "Back to the match", the newest caption starts "While you were answering:" and summarises what happened.
  3. No live question in the last 30 s before halftime or full time; it becomes a report replay.

### 17.1 Map from anywhere
- A **map button** (pitch-frame icon with two linked nodes, 44 px, `aria-label="Curriculum map"`) sits in the header of every screen after onboarding, just left of ⚙ / ✕: Matches, live, questions, reveals, the three-level screens, reports, Who's playing, Preferences, desktop panel. Spec in `design/Components` ("Map button").
- It opens the map as a full-screen sheet over the current screen. Its back button ("Close the map and go back to where you were") returns to the exact screen and scroll position.
- Opened mid-question, the question is saved for the break, the same as ✕. The live match keeps running underneath.
- Onboarding (Welcome, Pick your team) has no button; Welcome already links to all 20 concepts.
