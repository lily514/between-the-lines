# Milestone 2e Plan: Getting started

> Agreed 2026-10-16. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). 2e's branch is `feature/getting-started`.
> Milestone 2 so far: **2a** the loop in the terminal (f80be81), **2c** the web page (bad59de), **2d** the basics (5e3bedd). **2e is built before 2b** (the Tutor), as Lily chose on 2026-10-16.

## Context

A new viewer types a name and is sent straight into a match between two clubs they have never heard of. A beginner can't tell who is who, which players are which, or why they should care who wins. 2e adds the start a beginner needs: **pick a team to support, then meet both sides before each match.** What the team sheet shows grows as the viewer gets better.

The handoff's S7 (onboarding with placement checks) and S8 (preferences, including "favourite club") are the nearest designs. 2e takes only the favourite club from them. There are no placement checks: 2d's basics already start every new viewer on level 1.

**Decided (Lily, 2026-10-16):**
- **Pick a club once, at the start.** The viewer's three matches are that club's fixtures. The matches still never depend on the viewer's *knowledge*: choosing which team to follow is like a real fan choosing which match to watch.
- **"Your team" changes the presentation only.** Your club is named, listed first and highlighted on the pitch and in the score. The selector, the questions and the learner model don't change.
- **The team sheet grows with the viewer:** names, shirt numbers and positions in plain words first; then the formation and where each player stands; then stats from matches the viewer has already watched.
- **2e comes before 2b.**
- **The stage is your best concept's level** (by match number is the fallback, see Risks).
- **"Pick one for me" is offered,** for a beginner who has no reason to prefer a club.
- **A returning viewer with no club and no answers yet is offered the club choice.** Once they have answered, their record keeps today's fixtures.

**Not in 2e:**
- the handoff's placement checks and self-assessment;
- preferences (questions off, explanation level, player focus);
- different formations per club (every match is 4-4-2 today, see Risks);
- substitutions (the simulator has none, so the bench never plays);
- a league table or form guide (needs a simulated season of results);
- favouring your team's moments in the selector.

**Budget:** about 3 days, ending around 2026-10-21. 2b (about 4.75 days) then runs close to 2026-10-27, so 2e's cut list matters.

## How it works

```
name ─► new viewer? ─► Pick your team (10 clubs, or "Pick one for me")
                     │
                     ▼
        Welcome: "Your team: Hexham Anchors · Match 1 of 3: Hexham Anchors v Ripon Rooks"
                     │
                     ▼
        Who's playing (before every match): your team's eleven first, then the opponent's,
        a key to the pitch, and more detail as the viewer's level rises
                     │
                     ▼
        Kick off ─► MatchStep ─► questions, as now (your team highlighted)
```

**The club lives in the learner record.** `LearnerState` gets `club: TeamId | None`. `Course.fixture` picks the viewer's three matches from that club's 18 fixtures (with the same seed rule as now), so the terminal and the browser still share one record. A record with no club (every record made before 2e, and `btl learn` without `--club`) keeps today's fixtures exactly.

**The club can be changed until the first answer.** After that, the matches already watched belong to it, so the API refuses with 409.

**The team sheet comes from the server.** It is built from the same `pick_lineup` call the engine makes. A test checks that every player on it appears in that match's events and snapshots, and no one else does. Positions are named from the formation slot (a slot's `across` gives right, centre or left). The plain-word names and one-line descriptions are written once, in `league/positions.py`, so the terminal can use them too.

## Decisions

**What the team sheet shows, by stage.** The stage is the highest level the selector would give the viewer on any active concept (`level_for` of their best mastery). A beginner is always on stage 1, and one good concept is enough to open stage 2.

| Stage | Shows | Comes from |
|---|---|---|
| 1 | Club names, your team first; each starter's shirt number, name and position in plain words ("Left back: defends the left side, and joins attacks down it"), grouped goalkeeper → defenders → midfielders → forwards; a key to the pitch (filled discs and rings, the highlight for your team, numbers are shirt numbers) | `Lineup`, `league/positions.py` |
| 2 | Adds the formation ("4-4-2") and a small pitch with each starter where they stand at kick-off | The match's kick-off snapshot, so the picture is the match, not a diagram |
| 3 | Adds, per player, stats **from matches this viewer has already finished**: appearances, passes completed of those tried, line-breaking passes, threat added | `learn/player_stats.py` over the cached `PreparedMatch`es, using the line-breaking detector and the xT model |

- **Nothing from the coming match leaks.** Stage 3 counts only finished matches. The current match's events never feed the sheet, so the team sheet can't hint at a question. A test checks this.
- **Stats only for players the viewer has seen.** With a chosen club, your team's starters have stats from match 2 on. The opponent's players usually haven't been seen; their rows say "First time you've seen them". The page leaves the column blank and doesn't make up a zero.
- **The stage is in the response,** with the name of the next stage and what opens it ("Get to level 2 in any concept to see the formation"), so the viewer knows the sheet will grow.

**Backend.**
- `league/positions.py`: `position_name(formation, slot_index) -> Position` (short and plain names plus a description). Pure; no pandas.
- `learn/team_sheet.py`: `team_sheet(course, state, prepared, watched) -> TeamSheet`, a typed dataclass. `learn/player_stats.py`: `player_stats(prepared_matches, threat) -> dict[PlayerId, PlayerStats]`.
- `LEARNER_VERSION` 2: `club` is optional, and a version-1 file still loads.
- The API's prepared-match cache key becomes `(seed, club, match_number)`.
- **API:**
  - `GET /api/clubs` lists the clubs (id, name, short name).
  - `POST /api/viewers` takes an optional `club`.
  - `PUT /api/viewers/{id}/club` returns 409 after the first answer.
  - `GET /api/viewers/{id}/team-sheet` gives the sheet for the current match.
  - `your_team` (`"home"`, `"away"` or null) is added to the status, question and full-time payloads.
- **CLI:** `btl learn --club NAME`, and the terminal prints a stage-1 team sheet before each match. If time is short, this is the first thing cut.

**Frontend.**
- `PickTeam` screen (folder): the ten clubs as one radio group, keyboard first, plus "Pick one for me". That choice is made on the server from the name's seed, so the page invents nothing.
- `TeamSheet` screen (folder), shown between Welcome or full time and `MatchStep`: your team's card first, the opponent's below it (side by side on desktop), the pitch key, and the stage note. Stage 2 reuses `Shared/Pitch`.
- **Your team in the match:** a new token `--yours` in `tokens.css` (outline on your players' markers, a tint on your side of the score chip). Colour is never the only signal: the score chip also says "You".
- **Full time** says the result from your side ("Your team drew 1–1"), as plain fact.
- API types regenerated (`npm run api-types`).

**Accessibility.** Each team card is a list with its club name as the heading. Positions are words, not just abbreviations (`<abbr>` for "LB" at stage 2). The kick-off pitch is `aria-hidden`, because the list says the same thing.

## Tasks

| # | Task | Done when |
|---|---|---|
| 0 | Plan, CLAUDE.md | Plan committed; CLAUDE.md updated (below) |
| T1 | Your club in the record | `LearnerState.club`, version 2 (loads version 1); `Course.fixture` uses the club's fixtures; `start_session` and a `choose_club` that refuses after the first answer; `btl learn --club`. Tests: with a club, all three fixtures include it; without one, the demo viewer's attempt log over 3 matches is identical to before; a version-1 file loads |
| T2 | Positions and team sheets | `league/positions.py`; `learn/team_sheet.py` with stages 1 and 2; the stage from mastery. Tests: every slot of both formations has a name; the sheet's players are exactly those in the match's events and snapshots, over 40 seeds; stage 2's spots equal the kick-off snapshot |
| T3 | Stats from watched matches | `learn/player_stats.py`; stage 3. Tests on a hand-built mini match (< 15 events): passes, line-breaking passes and threat added by player. The current match never contributes, checked by comparing the sheet before and after answering every question in it |
| T4 | API | The routes and `your_team` above; cache key; 409 on a late club change. Tests with `TestClient`, including the leak check through the API. API types regenerated |
| T5 | Pick your team | `PickTeam` screen and the flow change in the reducer; Welcome shows your team. Tests for the reducer and screen, by keyboard |
| T6 ★ | Who's playing | `TeamSheet` screen at all three stages; your team highlighted on the pitch, score chip and full time. Tests for each stage and the "first time you've seen them" row. Lily plays as a new viewer in both themes, at phone and desktop width |
| T7 | Wrap-up | README "Try the web page" updated, with screenshots; implementation-notes summary; `--no-ff` merge |

Rough days: T1 0.5, T2 0.5, T3 0.5, T4 0.5, T5 0.25, T6 0.5, T7 0.25, so about 3.

## CLAUDE.md changes (commit 0)

- **Git workflow:** M2e "Getting started": `feature/getting-started`. 2c, 2d and then 2e are built before 2b.
- **What this is:** Milestone 2e adds getting started: picking a team to support, and a team sheet before each match that grows with the viewer.
- **Learning design rules:** add "The viewer's team chooses which matches they watch and how they are shown, never which moments are asked about. The team sheet uses only matches the viewer has finished."

## Risks and cuts

1. **Every match is 4-4-2.** Stage 2 always shows the same shape. Giving clubs their own formation would change every match, its seeded examples and the realism bands, so it is out of 2e. The plan notes it as a carry-over.
2. **A club's fixtures may be weaker for learning.** A low-strength club may give fewer settled line-breaks. The demo-viewer test runs with a club too, and must still reach line-breaking or counter-press questions by match 2.
3. **Threat added per player is noisy** over one or two matches. It is shown as the sum, with "in N matches", and never as a rating.
4. **Stage gating feels arbitrary.** If Lily finds it so in the hand check, the fallback is by match number (stage 2 from match 2, stage 3 from match 3).

**Cut order if short:**
1. `btl learn --club` and the terminal team sheet (the record still supports a club).
2. Stage 3's threat added (keep passes and line-breaking passes).
3. Stage 2's kick-off pitch (keep the formation name and position abbreviations).
4. The full-time line from your side.

## Verification

- `uv run pytest`, `uv run ruff check`, `uv run pyright`; `npm test`, `npm run lint`, `npm run build`.
- The demo viewer's attempt log without a club is byte-identical to main's.
- End to end with `btl serve` and a temporary learners folder: new name → pick a team → Who's playing (stage 1) → a whole match → full time → match 2's sheet shows your players' stats only if stage 3 is reached. Check that no team-sheet response holds anything from the current match.
