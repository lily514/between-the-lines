# Milestone 4 — Implementation notes

## T1 — Matches and calendar (2026-10-23)

**Plan said:** each match gives its state, plus the score and question count when finished.
**We did:** a match in progress also gives a score, and the match clock it stands at. Both are taken at the last moment
the viewer answered about, never later.
**Why:** the Matches board's "Live now" card shows a score and clock, and the stepped match has no live clock to read
them from. The last moment answered is a point the viewer has already seen, so nothing ahead of them leaks.
**Affects:** T6 shows it on the in-progress card as "at {clock}".

## T2 — Curriculum map and level words (2026-10-23)

**Plan said:** `GET /api/concept-map`, with the viewer's value and level word; settle whether five or six concepts are
askable.
**We did:** the route is `GET /api/viewers/{id}/concept-map`, beside the viewer's other routes. Five concepts are
askable: `ASKABLE` is the detectors with questions (`learn/questions.py`), and `counter_attack` has none, so
Transitions is "coming later" on the map, as the handoff says. Level words live in `learn/levels.py` and follow
`level_for`, with "Mastered" at the mastery threshold.
**Why:** the map carries the viewer's values, so it needs the viewer, like the matches and team sheet.
**Affects:** T7 calls the viewer's route.

## T3 — Reports (2026-10-23)

**Plan said:** a radar, in progress/mastered, a scout's note, up to 2 replay cards, and at full time a goal timeline and
recap, from `GET …/matches/{n}/report?at=…`; `FullTimeOut` points to it.
**We did:**
- **Asked-in period on each attempt.** Each attempt now records the period its question was asked in (`asked_in`),
  so a halftime report counts exactly the questions asked by the break. A review of a first-half moment asked in the
  second half doesn't count. The learner record is version 3; version 1 and 2 records still load, and their attempts
  fall back to the moment's own period.
- **Replay cards are the answers list.** Each question answered in the span gets one line: clock, concept, right or
  not. Moments held back from the last 30 s of a half are asked at the break before the report (T4), so they
  appear here too.
- **Reaching halftime.** The server checks it with a read-only replay (`ReadOnlyStore`): the match being watched has
  reached halftime once its next question is in the second half, or none is left.
- **The full-time summary is unchanged.** The page fetches the report by its `match_number`.

**Why:** without the period, a halftime report would either leak second-half reviews or have to guess.
**Affects:** T8 builds both report screens on `ReportOut`; T5 decides when the page shows halftime.

## T4 — Three asking rules (2026-10-23)

**Plan said:** one question per stoppage (the live basics question wins); no live question in the last 30 s of a half
(it becomes a replay); the step after feedback carries a "While you were answering" summary.
**We did:**
- **One per stoppage.** `SPACING` already kept two questions apart at any one dead ball (none in 800 questions over
  40 viewers). But 487 restart and foul moments come after the start of their own dead ball, so a saved review could
  take the stoppage first. A dead ball now holds its review when its own restart or foul will be asked.
- **Not near the whistle.** In the last 30 s before half-time or full time (`WHISTLE_MARGIN`), a settled moment is
  saved for the break. A restart or foul there isn't asked: CLAUDE.md says those are asked at their own stoppage or
  not at all, which beats "becomes a replay". A saved review waits for the break rather than a dead ball there.
- **Catch-up.** Each question now carries `score` (at delivery) and `catch_up`: a server-written line with the goals
  since the viewer's last answer in this match. The step shows it after "While you were answering:", and the step's
  score is now the server's for review questions too.

Over the same 40 viewers: 799 questions instead of 800, and 224 asked at the stoppage instead of 223.
**Why:** the rules hold by construction rather than by spacing luck; the catch-up needs goal facts the browser must
not compute.
**Affects:** nothing later; the demo viewer's attempt log changes slightly.

## T5 — Navigation shell (2026-10-23)

**Plan said:** `Shared/Header` with the map button and ⚙; an overlay layer for the map and preferences that restores
scroll; screens `matches` and `report`; first open Welcome → Pick → Matches, and return visits and "Done for this
match" → Matches; Welcome rebuilt to S7.
**We did:**
- **Overlay.** The header has the map button only; ⚙ comes with Preferences in T9. The map is an overlay over the
  screen, which stays mounted and hidden, so a half-answered question keeps its pick. Closing restores both scroll
  positions (the page's on a phone, the panel's on a wide screen) and puts focus back on the map button.
- **Return visits.** A remembered viewer now lands on Matches instead of jumping straight to the waiting question;
  "Rejoin the match" takes them there.
- **Start over** moved from the header to Matches.
- **Welcome needs the curriculum before there is a viewer,** so the API gained `GET /api/concept-map`, the map with no
  values.
- **The `report` screen comes in T8;** full time still uses the old summary, whose button now goes to Matches.

**Why:** the map from anywhere must not lose a pick in progress; the Welcome may show only what the API says.
**Affects:** T7 fills the map overlay; T8 adds the report screen; T9 adds ⚙.

## T6 — Matches screen (2026-10-23)

**Plan said:** next match + "See who's playing"; in-progress card with "Rejoin"; Your progress with level words and "See
your full map"; Earlier with report links.
**We did:** as planned, from the S0 board.
- The board's companion copy ("Put the match on your TV…", "● Live now", the saved-question count and the ±10 s
  sync) is replaced by stepped-match wording: "Part-way through · at {clock}", "{n} questions answered. The match
  waits for you."
- Earlier lists finished matches with their score; the report links arrive with the report screen in T8.
- With every match watched, the lead card says so.

**Why:** the live clock and saved questions are carried over to a later milestone.
**Affects:** T8 adds the report links.
