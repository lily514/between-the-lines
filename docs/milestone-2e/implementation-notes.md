# Milestone 2e: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## Summary (2026-10-21)

Milestone 2e is done, and Lily has checked it in the browser. A new viewer types a name, picks a team to support (or lets the page pick), and their three matches are that club's fixtures. Before each match, "Who's playing" shows both elevens, their team first. A beginner sees names and positions in plain words, level 2 adds the formation and the kick-off shape, and level 3 adds each player's numbers from matches already finished. The viewer's team is marked "You" and ringed on the pitch, and full time says the result from their side. Viewers without a club keep exactly the matches they had: the demo viewer's output is byte-identical to 2d's.

**Biggest changes from the plan**
- **Crests and club colours came in,** from a second design handoff made during the milestone. The crests arrived in T5 (the picker) rather than T6. They are one SVG sprite whose outline follows the theme; the club colours are tokens (T5, T6).
- **The club locks once match 1 is finished,** as well as after the first answer, so a match with no questions can't be watched and then swapped (T1).
- **Position names live in `sim/`, not `league/`,** because they come from formation slots (T2). The formation is now named once, `MATCH_FORMATION`, instead of being the simulator's default.
- **The full-time result comes from the API** (`your_result`), so the page still works out no football (T6).
- **Threat added uses the questions' format** ("+4.1%") everywhere (T4).

**Cut:** nothing from the cut list; the terminal got a team sheet at all three stages too.

**Carries over**
- **To 2b:** nothing in 2e changes the Tutor's work. The team sheet's words are fixed text, not worded by a model.
- **Open points:**
  - Line-breaking counts on the sheet are generous (17–19 a match for a central midfielder); counting only `MIN_FORWARD` passes is a one-line change if they look wrong.
  - Every club plays 4-4-2.
  - Stage 1 is long on a phone.
  - The left back wears 5, not 3.
  - The design handoff asks for each town name to be checked against real local clubs before launch; that check belongs in the private, gitignored list.

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

## T3 — Numbers from watched matches (2026-10-17)
**Plan said:** `learn/player_stats.py`; stage 3. Tests on a hand-built mini match for passes, line-breaking passes and threat added by player; the current match never contributes.
**We did:** as planned, with these choices:
- **`watched_numbers`** takes each finished match's context and its starters, and returns each starter's numbers plus how many watched matches each club played (for the page's "From the N matches of theirs you have watched").
  - **Passes** are ordinary passes and crosses. Set pieces don't count, or every player would collect some just for standing nearest when the ball went out.
  - **A starter who never touched the ball has real zeros.** A player in no watched match has no entry at all, and the sheet shows "first time you've seen them".
- **`viewer_sheet(course, state, prepare)`** works out the stage and, from stage 3, the numbers; `finished_numbers` asks `prepare` for matches 1 to N − 1 only. The leak test checks exactly that: the numbers never ask for the current match.
  - Below stage 3, no earlier match is prepared at all.
- **The terminal shows stage 3 too:** four columns (matches, passes completed/tried, line-breaking, threat added), "first time you've seen them" for unseen players, and a line for a club not yet watched.

**Learned:** the detector finds many line-breaking passes: about 17–19 a match for a simulated centre midfielder. The simulator's flat lines make short passes between level midfielders count, as the `MIN_FORWARD` note in `candidates.py` already says. Questions use only the clearer ones; the sheet counts all of them, as the plan says.
**Why:** the plan left these details open.
**Affects:** T4 (the team-sheet route calls `viewer_sheet` with the API's cached `prepare`). If the counts look too high in Lily's T6 check, the sheet could count only passes that go `MIN_FORWARD` metres forward, the same rule questions use.

## T4 — API (2026-10-17)
**Plan said:** `GET /api/clubs`; `POST /api/viewers` takes an optional `club`; `PUT /api/viewers/{id}/club` (409 after the first answer); `GET /api/viewers/{id}/team-sheet`; `your_team` on the status, question and full-time payloads; the cache key; the leak check through the API; API types regenerated.
**We did:** as planned, with these additions and choices:
- **Every new field is added beside the old ones,** so the page keeps working unchanged until T5 and T6 use them:
  - the status, question and full-time payloads carry each club's three-letter code (`home_code`, `away_code`), the key for the handoff's crests and colours;
  - the status also carries `club`, `can_choose_club` and `suggested_club`.
- **"Pick one for me":** `suggested_club` is the viewer's seed modulo the number of clubs, so a name always suggests the same club. Pressing it again moves the page on to the next club in the list.
- **Starting with a club** sets it while the viewer can still choose. Asking again for the club they already have is fine at any time; a different club after the first answer is a 409, as with `PUT`.
- **The team sheet route** returns 409 for a viewer who has watched every match. Kick-off spots are rounded to 0.1 m.
  - `next_stage` carries the wording that says what opens more ("Get to level 2 in any concept to see the formation."), written once in `team_sheet.NEXT_STAGE`. The terminal shows it too.
- **Threat added uses the questions' format,** percentage points such as "+4.1%". The formatter, `percent_points`, is now public in `evidence.py`, and the terminal's stage 3 column uses it too.
- **`question_payload` takes the two clubs** and the viewer's club rather than two names.
- **The leak check through the API** plays the demo viewer to match 3, which reaches stage 3. Each club's `matches_watched` matches matches 1 and 2 exactly, and the players' numbers don't change after answering a question in match 3.

**Why:** the plan left these details open; the codes are for the crests the design handoff added.
**Affects:** T5 and T6 read the new fields. The page's hand-built test payloads gained the new fields.

## T5 — Pick your team (2026-10-17)
**Plan said:** a `PickTeam` screen: the ten clubs as one radio group, keyboard first, plus "Pick one for me"; the flow change in the reducer; Welcome shows your team.
**We did:** as planned, with these choices:
- **The crests arrive here, not in T6.** The handoff's picker rows have them, so `Shared/Crest` draws them now, and the welcome uses them too.
  - They come from one sprite, `src/assets/crests.svg`, built from the handoff's dark files with only the outline changed. Each `<use>` picks a club's symbol.
  - The outline is `var(--crest-outline)`, which is `--text`. That gives exactly the handoff's two outline colours (`#F6EDE4` on dark, `#2B1018` on light), so one file serves both themes.
  - The club colours (the 4 px bar on the team-sheet cards) come with T6.
- **Who is asked:** a new viewer is asked after their name, before the welcome. So is a returning viewer with no club and no answers, as decided. There is no "skip": "Pick one for me" is the beginner's way through.
- **The wording** says "You can change this until your first question", not the handoff's "any time in Preferences": the club locks after the first answer (T1), and there are no preferences in 2e. The handoff's "Last step" eyebrow is left out, since the picker isn't always reached from the name.
- **The welcome** shows "Your team: {crest} {club}" with a "Change" link while the club can still change. A 409 when choosing (the viewer started watching in another tab) shows the welcome as it now stands.
- **"Pick one for me"** selects the server's suggestion, then the next club on each press. A polite live region says which club was picked, since the radio's change alone isn't announced.

**Learned:** a `--` inside an XML comment makes the whole SVG invalid, and browsers then draw nothing from the sprite, silently. The sprite's comment had `--crest-outline` in it. A test now parses the sprite and checks it has a crest for every club, and it fails on that comment.
**Checked in the browser** (`btl serve`, headless Chrome): the picker, "Pick one for me" and the welcome, at 390 px in both themes and at 1440 px, with no console errors.
**Why:** the handoff put crests in the picker; the club lock and the lack of preferences change the wording.
**Affects:** T6 (the team sheet reuses `Crest`, and adds the club colour tokens).

## T6 — Who's playing (2026-10-21)
**Plan said:** a `TeamSheet` screen at all three stages; your team highlighted on the pitch, the score chip and full time; tests for each stage and the "first time you've seen them" row; Lily's hand check.
**We did:** as planned, with these choices:
- **Where it appears:** "Watch match N" on the welcome and "On to match N" at full time both open the team sheet; "Kick off" then goes to the first step. A remembered viewer who reloads mid-match still goes straight back to their question. "Not your team? Change it" appears while the club can change.
- **The sheet**, from the handoff's TS boards:
  - **The key:** filled disc for home, ring for away, a dashed ring and "You" for your team, and that numbers are shirt numbers.
  - **A card per side:** crest, name, code, "Home · filled discs" or "Away · rings", and the formation from stage 2. A 4 px bar runs across the top in the club's colour.
  - **The players** are listed by position group. Each row has the shirt number drawn as on the pitch, the name, and the position in words with its description; stage 2 adds the abbreviation.
  - **Stage 3** adds a 2 × 2 grid of numbers per player, "First time you've seen them" for players not seen yet, and a line per club saying how many of its matches the numbers come from.
- **Your team's card** has a 2 px outline, the raised fill and a "You" tag.
- **The kick-off shape (stage 2 on)** reuses `Shared/Pitch` with two new options: `yours` (a dashed ring round your players) and `ball={false}`, since a line-up has no ball. It is hidden from screen readers; the lists say the same.
- **During the match:** question and feedback pictures ring your players in the same way, and the step's fixture tags your club "You".
- **Full time** says "Your team, Ludlow Ferrymen, lost 1–2.", with your team's goals first. The result itself comes from the API (`your_result` on the full-time payload, new here), so the page works out no football.
- **Colours:**
  - The club colours are tokens in `tokens.css` (`--club-HEX` and so on), each club's dark and light primary from `clubs.json`; the colour lint allows literals only there.
  - `--yours` is butter (`#F2CF6E`), drawn dashed on the pitch, which looks the same in both themes.
- **Tests:**
  - each stage, from real payloads captured from the API (a new viewer at stage 1; a Hexham fan at match 3, stage 3; stage 2 derived from it);
  - the key, and that no zeros are shown for unseen players;
  - the result line, the "You" tag, and the whole flow from welcome to sheet to step, and from full time to the next sheet.

**Checked in the browser** (`btl serve`, headless Chrome, learner records made with the server's own threat model): stage 1 in both themes at 390 px and at 1440 px; stage 2 and stage 3 in both themes; the step and a question picture. No console errors.
**Learned:** stage 1 is long on a phone (about 2,700 px), because each of the 22 players carries its position description. That is what the plan asked for. If it feels like too much in Lily's check, the fallback is to describe each position once per group, or only for the viewer's team.
**Why:** the plan left the layout to the handoff, and the result line needed one field from the API.
**Affects:** T7 (README screenshots). **Lily's hand check is still to do.**
