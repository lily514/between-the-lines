# Milestone 1: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## Summary (2026-10-07)

Milestone 1 is done: every task from T1 to T15 is in, including the cuttable ones (the counter-press detector and template, and the counter-attack detector).

**Biggest changes from the plan**
- **Detectors read typed events, not a DataFrame.** `MatchContext` holds a `Match` seen left to right, so pandas stays in the edge modules (T10).
- **Names.** Clubs are named after real towns with no professional club, players have real first names and invented surnames, and no real names are in the repo, not even as a list of names to avoid. A private, gitignored list checks them locally (T4).
- **Planting.** The engine asks an optional director for each possession's opening and never imports `plant/`. Scripts can hand the ball to the other team, which a counter-press needs. The learner's picture is the snapshot just after play pauses (T13, T14).
- **Bands checked against real matches.** Counting the same measures in 40 real matches from StatsBomb's open data corrected the throw-in band and added goal-kick, throw-in and touchline bands (T8).
- **The sample match is about 800 KB**, not 100 KB, because it keeps every player's position at every event (T15).

**Cut:** the `ordering` option for planted moments (always easiest first), and a simulator version in the threat model file (there is none to record).

**Added beyond the plan:** `btl matches`, and `btl replay`, an animated replay of each planted moment (T15's stretch goal).

**Carries over**
- Where the simulator differs from real matches, with no band yet: about 9 switches of play per match against about 20 real, 0.9 counter-attacks against 3, probably too many line breaks (about 205), long goal kicks, and slightly fewer throw-ins.
- Only the line-breaking detector gives a difficulty. The counter-press rule would need a fix for loose balls before running on real data (T12).
- The sample match must be regenerated whenever the simulator changes; the README gives the command.
- The replay's frame builder (`btl/replay.py`) is pure and could feed the web pitch. On the ASCII pitch, motion is steppy (one character is 2 m by 4 m), and players jump a few metres into a planted moment's scripted positions.

## T1 — Project skeleton (2026-10-07)
**Plan said:** pin Python with `uv python pin 3.11` so the project doesn't depend on pyenv.
**We did:** also set `python-preference = "only-managed"` under `[tool.uv]` in `pyproject.toml`.
**Why:** with only the pin, uv picked an existing Anaconda Python 3.11.4 from the search path. The pin fixes the version, not where the interpreter comes from.
**Affects:** nothing; `docs/setup.md` includes `uv python install 3.11`.

## T2 — socceraction trial run (2026-10-07)
**Plan said:** pin socceraction exactly; if it fights modern packages, first try pinning older versions.
**We did:** pinned `socceraction==1.5.3`, and constrained `multimethod<1.11` via `constraint-dependencies` in `pyproject.toml`.
**Why:** socceraction caps pandera at 0.17, and pandera 0.17 imports `multimethod.overload`, which was deprecated in multimethod 1.11 and removed in 2.0. Without the constraint, `import socceraction.spadl` fails. The rest of the stack resolves fine: numpy 1.26.4 (socceraction caps it below 2), pandas 2.3.3, scipy 1.17.1.
**Affects:** nothing yet. The pin is the first thing to revisit if we ever upgrade.

## T2 — Discoveries in socceraction (2026-10-07)
**Plan said:** keep extension fields in a separate frame "even if its schema is strict"; verify the coordinate convention.
**We did:** confirmed both. `SPADLSchema` is strict and rejects extra columns. Converters store the home team attacking left → right in both periods, exactly as planned.
**Why it matters:** two surprises for T9. Expected Threat's interpolation option is broken (SciPy removed `interp2d`), so we use the plain 16 × 12 grid. And `save_model` writes only the bare grid, so our model file with fitting details (matches, seed, simulator version) will be our own JSON format.
**Affects:** T9.

## T2 — Pyright and socceraction (2026-10-07)
**Plan said:** only edge modules may relax type checking, with `# pyright: basic`.
**We did:** also set `reportMissingTypeStubs = false` project-wide.
**Why:** socceraction has inline type hints but no `py.typed` marker. Without this setting, every import of it is an error, even in files that are otherwise fully typed. It's narrower than switching whole files to basic mode.
**Affects:** nothing.

## T3 — Schema (2026-10-07)
**Plan said:** `Match` holds meta, teams, events, the position array, and planted moments; the position array is events × 22 × 2.
**We did:** `Match` holds only the game id, the two team ids, the events, and optional positions. Positions cover any number of tracked players, each described by a `PlayerSlot`, with `NaN` for unknown positions.
**Why:** the league, its clubs, and planted moments don't exist yet. Each will be added to `Match` by the task that creates it (T4 and T13). A fixed 22 would rule out the partial snapshots the plan says other data sources may supply, and would make small test fixtures needlessly large.
**Affects:** T4 and T13 extend `Match`.

## T3 — Smaller schema choices (2026-10-07)
**Plan said:** no detail on these.
**We did:** `original_event_id` is derived from the game and action ids (`"g1-e0003"`), not stored. Direction flipping is a `left_to_right=True` option on `to_spadl_frame` and `to_snapshot_frame`, not a separate function. The possession rule is written up in `docs/event-schema.md`.
**Why:** the fewest moving parts; the flag keeps every flip inside `frames.py`, as planned.
**Affects:** nothing.

## Editor setup (2026-10-07)
**Plan said:** nothing about editor configuration; `.vscode/` was gitignored in T1.
**We did:** committed `.vscode/settings.json` and `.vscode/extensions.json`; everything else in `.vscode/` stays ignored.
**Why:** with the repo root open, VS Code used a system Python and global Flake8/Pylint, which don't know the project lives in `backend/` or read its ruff and pyright settings. That gave false "line too long" and "import could not be resolved" errors. Committed settings also prepare the future Codespace.
**Affects:** the dev container milestone can reuse these settings.

## T4 — No real names in the repo (2026-10-07)
**Plan said:** a denylist test of real clubs and well-known players.
**We did:** no list of real club, player, or league names in any committed file. A private list in `backend/private/real-names.txt` (gitignored) drives `tests/league/test_real_names.py`, which is skipped when the file is absent. It checks the name pools themselves, so no seed can produce a listed full name, and also scans 200 generated leagues. Before the first push, we also reworded the plan and CLAUDE.md so they don't name the league the hackathon is associated with.
**Why:** real names in the repo, even in a list of names to avoid, could conflict with the hackathon rules.
**Affects:** CI can't run the real-name check; it's a local step in `docs/setup.md`.

## T4 — Real towns and first names, invented surnames (2026-10-07)
**Plan said:** a fictional league built by a small name generator.
**We did:** after trying names built entirely from invented syllables, we switched to:
- clubs named after real English market towns with no professional club, plus invented nicknames ("Kendal Kestrels");
- real common first names from birth registries for each style;
- invented surnames, so a full player name is never a real person's on purpose.

Sources, and which pools were checked against registry data, are in `docs/name-sources.md`. Checking the five largest pools against registry rows confirmed 145 of 150 names; the other 5, plus one spelling in each of two pools, were replaced.
**Why:** syllable-built names read as fake. Real surnames were ruled out because common first names and common surnames together rebuild real players, ordinary squad members as well as stars, and blocking them would need a private list of every recent top-flight player.
**Affects:** nothing downstream; `League` and `Player` are unchanged.

## T4 — League details (2026-10-07)
**Plan said:** `generate_league(seed)`; 10 clubs × 20 players with positions and shirt numbers.
**We did:** `generate_league(rng)` takes a `numpy` Generator, as CLAUDE.md requires for all randomness; tests build one from a seed. Each club also gets a three-letter short name and a `strength` between 0.85 and 1.15 for the simulator to use. Squad roles are GK/DF/MF/FW with traditional shirt numbers. Player names come in nine styles, weighted to roughly match the real league the hackathon is about (see the next note). No two clubs share a town or a nickname, and no club has two players with the same first name or the same surname. `season_fixtures` builds a double round robin (90 matches) for batch runs. The league name is fixed: "Meridian League".
**Why:** CLAUDE.md's randomness rule; strength and fixtures are what T6 and T9 need from a league.
**Affects:** T6 uses `strength`; T9 can fit Expected Threat on a season of fixtures.

## T4 — Name style weights (2026-10-07)
**Plan said:** nothing; names were to be fictional.
**We did:** weighted the nine name styles to roughly match the nationalities in the real top-flight English league, 2025/26:

| Style | Weight | Mainly standing in for |
|---|---|---|
| British | 28% | England, Scotland, Wales, Northern Ireland, Ireland, other English-speaking countries |
| Dutch and German | 16% | Netherlands, Germany, Flemish Belgium, Austria, Switzerland |
| French | 12% | France, French-speaking Belgium |
| Portuguese-speaking | 12% | Brazil, Portugal |
| Spanish-speaking | 12% | Spain, Argentina, Uruguay, Colombia, Ecuador, Mexico |
| West African | 8% | Nigeria, Senegal, Côte d'Ivoire, Ghana, Cameroon, Mali, DR Congo |
| Nordic | 6% | Denmark, Norway, Sweden, Iceland, Finland |
| Slavic | 3% | Serbia, Croatia, Poland, Czechia, Ukraine |
| North African | 3% | Morocco, Algeria, Egypt, Tunisia |

**Sources and estimates:** the season's counts for the largest groups come from Transfermarkt figures reported in the press (France 40 of about 390 players, Netherlands 36, Brazil 31, Spain 21, Germany 15, Argentina and Portugal 14 each, Belgium 12; 65 nationalities). Smaller nations aren't in that list, so their sizes are estimated from the league's own all-time count of players by nation, scaled to this season. No current count of English players was available; the British share is the remainder, consistent with squad rules that cap non-homegrown players at 17 of 25. Italian, Greek, Turkish, and East Asian players (a few percent together) have no style of their own.
**Why:** Lily asked for squads that sound like a real league's, not mostly English.
**Affects:** nothing; `pick_style` is tested to produce these proportions.

## T6 — Simulator core (2026-10-07)
**Plan said:** `simulate_match(home, away, seed)`; the actor is a player whose formation role fits the zone; open play only.
**We did:**
- The signature also takes keyword-only `game_id` (defaults to the seed), `home_formation` and `away_formation` (default 4-4-2), `with_snapshots`, and `params`.
- New module `sim/lineup.py` picks each club's starting eleven: the first squad members of each role.
- The actor is the player whose spot in the team's shape, without jitter, is nearest the ball. A pass goes to the teammate nearest where it lands; a dribble keeps the same player. Choosing players never uses the shape model's random stream, so turning snapshots off leaves the events unchanged (tested).
- A possession that starts by winning the ball opens with the winning action (interception, tackle, keeper save or claim), so the engine's `possession_id` and `schema/possession.py` agree by construction. The possession test confirms this on every event.
- Snapshots are taken at the start of each action. For the action that wins the ball, the shape is still the other team's attacking shape.
- With no restarts yet: a kickoff is a set-piece pass backwards from the centre spot (start of each half, and after a goal). After a missed shot, the keeper takes a set-piece pass from the six-yard box (T8 turns it into a goal kick). Passes and dribbles end at least 1 m inside the lines, so the ball never goes out.
- Dribbles can fail (the opponent's tackle wins the ball); there are no separate take-ons.
**Why:** the simplest model that meets the T6 invariants. The rule for choosing actors also means passes in natural play end where a teammate stands, which the line-breaking detector (T11) needs.
**Affects:** T8. Before any calibration, a match takes about 0.14 s (0.03 s without snapshots) and has about 2,200 events, 1,300 passes (75% completed), 43 shots, and 3.5 goals. Passes and shots are above T8's bands. Strength now moves each success's *odds* by (strength ratio) ** 0.5. The first draft used ** 2, which compounds over a possession: the stronger side took up to 9 in 10 of the shots. T8 should keep this in mind. `sim/stats.py` (summary stats for band tests) is left to T8, where those tests live.

## T7 — CLI and saved matches (2026-10-07)
**Plan said:** all file reading and writing lives in `btl/io.py`, with parquet for tables; CLAUDE.md allowed pandas only in `schema/frames.py`, `value/`, and `cli/`.
**We did:** added `io.py` to CLAUDE.md's list of pandas edge modules, so it may also start with `# pyright: basic`. Added `pyarrow` as a dependency; pandas needs it for parquet.
**Why:** the plan and the rule conflicted. Writing parquet means calling pandas, and pandas' parquet functions fail strict pyright. Moving the reads and writes into `frames.py` would have broken the other rule, that I/O happens only in `io.py` and `cli/`.
**Affects:** nothing.

## T7 — Saved match details (2026-10-07)
**Plan said:** `meta.json` holds the seed, clubs, schema version, and planted moments; `btl simulate --seed 7 --out runs/`.
**We did:**
- `meta.json` holds the schema version, game and team ids, the match seed, the league seed, and both formations. Club and player names aren't saved. `btl events` regenerates the league from its seed to name them.
- Without `--home` and `--away` (club short names), `btl simulate` takes the clubs from the league's season fixtures, using the seed to choose. `--out` defaults to `data/matches`.
- `btl events` shows 50 events by default; `--start` and `--count` choose others.
- Planted moments arrive with T13.
**Why:** the league is fully determined by its seed, so saving names would only duplicate it. Showing all 2,000+ events at once was unreadable.
**Affects:** T15. A saved simulated match is about 1.1 MB, mostly `positions.parquet` (about 47,000 rows of 64-bit floats). The plan expects the committed sample match to be about 100 KB, so T15 will need a shorter match, rounded or 32-bit positions, or a larger budget. If the name pools change, old saved matches show new names; the ids and events stay valid.

## T8 — Restarts and calibration (2026-10-07)
**Plan said:** kickoffs, throw-ins, goal kicks, corners; band tests over 50 seeds (passes 700–1100, completion 70–88%, shots 15–35, mean goals 1.5–4); stop tuning when they pass.
**We did:**
- A failed pass carries on past its target by up to 8 m. If that takes it off the pitch, it goes out where it crosses the line: over a touchline it's the other team's throw-in from that spot, over the goal line being attacked their goal kick, over the passer's own goal line their corner. Otherwise an opponent intercepts it, as before.
- Corners also come from failed crosses (15% are deflected out) and missed shots (10%). The ball stays with the attacking team, so the corner is part of the same possession; there is no defender event for the deflection.
- Missed shots now lead to a `goalkick`. Throw-ins use body part `other`. Corners are 80% `corner_crossed` (treated like a cross, so a header can follow) and 20% `corner_short`.
- Each restart costs dead-ball time: throw-in 12 s, goal kick 20 s, corner 25 s (a goal is still 45 s).
- `Start` now says how a possession begins with either `won_with` or a `restart` kind, never both, replacing the old `kickoff` flag.
- New `sim/stats.py` counts passes (SPADL `pass` only; crosses and restarts are counted separately), shots, goals and restarts. `tests/sim/test_calibration.py` holds the bands. Each band must hold for the mean over the 50 seeds **and** for at least 90% of single matches, so a good average can't hide wild matches.

Over 50 seeds, after tuning:

| | Before T8 | After | Band |
|---|---|---|---|
| Events | ~2,200 | 1,658 (1,526–1,752) | — |
| Passes | ~1,300 | 961 (851–1,070) | 700–1,100 |
| Pass completion | 75% | 75% (73–77%) | 70–88% |
| Shots | 43 | 25.4 (14–33) | 15–35 |
| Goals | 3.5 | 2.3 (0–6) | mean 1.5–4 |
| Throw-ins / goal kicks / corners | — | 57 / 24 / 11 | — |

Most of the drop in passes came from dead-ball time alone. Tuning was then just shot frequency (`shot_share_in_box` 0.35 → 0.22, `shot_share_in_range` 0.06 → 0.035) and how often restarts happen.
**Why:** the bands are the definition of done, so tuning stopped once they passed.
**Affects:** Two things look unrealistic but aren't covered by a band, so we left them. Throw-ins (~57) and goal kicks (~24) run above real matches (roughly 40 and 17), because wide passes are often aimed off the pitch in the first place. Successful wide passes are clamped 1 m inside the touchline, so a lot of play runs right along it. Both could matter for how snapshots look in T13. A match now takes about 0.11 s (0.03 s without snapshots).

## T9 — Expected Threat (2026-10-07)
**Plan said:** `btl fit-xt --matches 200 --seed 0` saves the model deterministically, along with how it was fitted (matches, seed, simulator version); `btl events` shows an xT column.
**We did:**
- `btl fit-xt` also takes `--league-seed` and `--out` (default `data/models/expected-threat.json`). `--seed` draws one seed per match; the matches follow the season's fixtures in order. It prints the grid as a heat map, which makes it the first thing worth showing about threat.
- The model file holds the grid, the number of matches and actions, the seed, and the league seed, plus a format version so old files fail loudly. There's no simulator version to record, because the project has none. A refit is the way to pick up simulator changes.
- `btl events` adds a `threat` column when a model exists at `--model` (by default the same path). Otherwise it leaves the column out and says to run `btl fit-xt`.
- `ExpectedThreat.fit` prints its iteration count to stdout, so `fit_grid` swallows it to keep the CLI's output clean.
- The fast tests fit on 20 matches (about 2 s). The 200-match fit runs only with `pytest -m slow`, as CLAUDE.md planned.
**Why:** the extra options keep tests and experiments away from the real model file. The rest is the simplest way to meet the plan.
**Affects:** T10's `MatchContext` can take threat values from `rate_match`. The CLI test that runs `btl events` now passes `--model`, so it never reads a model from the real `data/` folder.

## T8 — Throw-in length band (2026-10-07)
**Plan said:** T8's bands cover passes, completion, shots, and goals.
**We did:** added a fifth band, for throw-in length: mean 8–20 m, 2–15% of throws 20 m or more, none over 40 m. Throws are capped at 32 m (`throw_in_longest`); a longer random length is drawn again. `MatchStats` now also records each throw-in's length.
**Why:** a 25 m throw showed up in a sample match, and the longest throw over 50 seeds was 53 m, close to the world record of about 51–60 m set outside matches. In real matches a "long throw" is 20 m or more, and the longest are in the low 30s of metres; teams take about 4 long throws in about 39 throw-ins per match in the current top-flight season (sources: the league's own article on long throws in 2025/26, and The Analyst on throw-ins). The 40 m limit leaves room for a failed throw that runs on 8 m before going out. Before the cap: mean 10.0 m, 10% long, longest 53.4 m. After: 9.7 m, 9%, 33.5 m.
**Affects:** every match after its first capped throw changes, because the random draws shift. The other bands still pass with nearly the same numbers (passes 964, completion 76%, shots 26, goals 2.2). The grid in `expected-threat.md` was refitted; it keeps its shape and its 13% peak.

## T8 — Passes no longer hug the touchline (2026-10-07)
**Plan said:** nothing about this; the T8 note flagged it as left alone.
**We did:**
- A pass or dribble aimed off the pitch now has its target reflected back in across the line, like a ball bouncing off a wall, instead of being pinned 1 m inside it. A target 5 m beyond the touchline becomes one 5 m inside it. New helper: `reflect_into_pitch` in `sim/pitch.py`.
- A failed pass now runs on from that reflected target. So the ball goes out only when a pass misses and carries on over a line, not because it was aimed out. To keep enough throw-ins, the run-on range grew from 0–8 m to 0–20 m.
- Two new bands: 25–50 throw-ins per match (real matches average about 39), and at most 10% of actions starting within 2 m of a touchline. `MatchStats` gains `actions` and `on_touchline`.
- The throw-in length band now measures only successful throws, from the thrower to the teammate who got it, and its limit tightens from 40 m to 35 m. With a 20 m run-on, a missed throw could roll out 40 m or more from where it was taken, which says nothing about how far it was thrown.

| Over 50 seeds | Before | After |
|---|---|---|
| Actions within 2 m of a touchline | 18% | 6.5% |
| Throw-ins | 56 | 34 |
| Goal kicks | 24 | 27.5 |
| Passes | 964 | 1,010 |
| Shots | 26 | 28.5 |
| Goals | 2.2 | 2.2 |

**Why:** about 1 in 6 actions happened right on the touchline (an even spread would give about 6%), because wide passes were pinned to the line and the next pass from there was pinned again. It looked wrong, and it inflated throw-ins. Making the ball go out only when a pass misses is closer to how play really stops. We tried running on from the original off-pitch target instead: that left 52 throw-ins per match. The touchline share has no published figure that we know of; 10% is our own limit, set against the 6% of an even spread.
**Affects:** every match changes, so seed 7 is now a 0-0 draw. Goal kicks rise to about 27.5, because more missed forward passes run over the goal line; real matches have fewer, but there's no band for them. The threat grid in `expected-threat.md` was refitted: same shape, peak about 12%. T13's snapshots should look more natural on the wings.

## T8 — Bands checked against real match data (2026-10-07)
**Plan said:** band tests with ranges for passes, completion, shots and goals; no source for the ranges.
**We did:** counted the same measures in real event data and set or corrected the bands against it.
- **Source:** StatsBomb's free open data (github.com/statsbomb/open-data), which holds every match of the 2015/16 season of the real top-flight English league. We took 40 matches at random and counted with a throwaway script. Neither the data nor the script is in the repo. "Passes" there means open-play passes and kickoffs, matching `MatchStats`. "On a touchline" means a pass, carry or shot starting within 2 m of one.
- **Goal kicks:** half the simulator's 27.5 per match came from passes overhit over the goal line. Now, when a failed pass would run over the goal line in front of goal (the width of the penalty area), the keeper picks it up 2 m before the line 90% of the time (`keeper_pick_up_share`, SPADL `keeper_pick_up`). The extra open play pushed passes up, so the time to control a pass grew from 0.8–3.0 s to 1.2–3.8 s. New band: 10–25 goal kicks per match.
- **Throw-in length: the earlier band was wrong.** The figures it used ("about 4 long throws a match, the longest in the low 30s of metres") count only throws of 20 m or more *into the box*; we had read them as covering all throws. In the real data, 24% of successful throws go 20 m or more, and 1 in 100 goes 39 m or more. The mean throw before misses and the cap is now 18 m (was 12 m), and the cap is 40 m (was 32 m). The band is now: mean 10–20 m, 15–35% of throws 20 m or more, none over 45 m.
- **Throw-in count:** the band widens to 25–55 to cover both the real 48 here and the about 39 reported for recent seasons.
- The band test's comments now give the real figure next to each band.

| Per match | Real (40 matches) | Before | After | Band |
|---|---|---|---|---|
| Goal kicks | 16.8 (9–27) | 27.5 | 17.5 | 10–25 |
| Throw-ins | 47.8 (26–70) | 34 | 35 | 25–55 |
| Corners | 10.0 | 10.5 | 9.5 | — |
| Passes | 717 (553–944) | 1,010 | 959 | 700–1,100 |
| Pass completion | 79% | 75% | 75% | 70–88% |
| Shots | 25.2 | 28.5 | 24.8 | 15–35 |
| Goals | 2.7 | 2.2 | 2.1 | mean 1.5–4 |
| Actions within 2 m of a touchline | 6.0% (3.6–8.7%) | 6.5% | 6.4% | at most 10% |
| Successful throw-ins: mean / 20 m or more / longest | 15.6 m / 24% / 51 m | 11.2 m / 10% / 32 m | 14.3 m / 23% / 40 m | see above |

**Why:** Lily asked for goal kicks to be checked against real matches, and checking the rest at the same time showed the throw-in band was based on a misread figure.
**Affects:**
- **Era caveats.** The data is ten years old. Counts of restarts depend on the ball going out, so they should still hold, but how they are taken has changed. In 2015/16 most goal kicks were long (median 61 m); since a 2019 law change most are played short. Teams also pass more now, so 717 passes is likely low for today's game.
- **Left as is:** the simulator's goal kicks stay long (mean 35 m), and its throw-ins stay below the real 48. Both are in band.
- **Every match changes again.** The grid in `expected-threat.md` was refitted: same shape, peak about 12%.

## T10 — Detector framework and switch of play (2026-10-07)
**Plan said:** `MatchContext` bundles the SPADL frame (with names), snapshots, possessions, and xT; `ConceptId` covers the four concepts; detectors return a `list`; `concepts/` depends only on `schema/` and `value/`.
**We did:**
- `MatchContext` holds a typed `Match` seen left to right, not a DataFrame. CLAUDE.md keeps pandas out of everything but `frames.py`, `io.py`, `value/` and `cli/`, and detectors read better as loops over `Event`s. The context's snapshots come from the same flipped match, so an action and its snapshot are always flipped together.
- New `to_left_to_right(match)` in `frames.py`, the one place that flips coordinates. The frame functions' `left_to_right=True` now use it instead of socceraction's `play_left_to_right`, and a test checks that the two give the same frame.
- The pitch's length and width moved to `btl/schema/__init__.py` (re-exported by `sim/pitch.py`), so detectors can use them without importing the simulator.
- `ConceptId` has only `SWITCH_OF_PLAY` for now; each later detector task adds its own member. Otherwise the test that every concept has a detector would fail until T14.
- `detect` returns a tuple, matching the rest of the code. A test parses every module in `concepts/` and fails if one imports `sim`, `plant`, `league`, `cli` or `io`.
- Switch of play, as written in the detector's docstring: a successful pass or cross at least 30 m across, ending in the outer third of the pitch's width on the other side of the centre line from where it started. No difficulty is given. The evidence is the distance across.
- `btl tags <match>` lists tags, optionally just one concept (`--concept switch_of_play`).
**Why:** the CLAUDE.md rule on pandas, and keeping detectors free of the simulator.
**Affects:** T11–T14 add a `ConceptId` member and a line in `ALL_DETECTORS` each. T15's `btl inspect` can join tags to events by `action_id`.

**Checked against real data.** On the 40 real matches from the T8 note, our rule finds 19.9 switches per match. StatsBomb's analysts flag 14.7 passes per match as switches, and our rule catches 13.3 of them (90%). StatsBomb doesn't flag the other 6.6, and its exact definition isn't published with the data, so we can't say which side is stricter where. Simulated matches have only about 9 per match, so the simulator plays fewer long cross-field passes than real teams do. There's no band for this yet. The rule also counts passes across a team's own penalty area, which real definitions count too, but which make weak teaching examples. A later task could require the pass to start outside the team's own third.

## T11 — Line-breaking detector (2026-10-07)
**Plan said:** group the opposition's outfield players into lines by x; a successful pass that starts behind a line of at least 3 players and ends beyond it breaks that line; difficulty from the gap width at the crossing point and the number of lines broken.
**We did:** as planned, with these choices written into the detector's docstring:
- A new line starts wherever the next defender (sorted by x) stands more than 5 m further up the pitch. In simulated play, players within a line are under 4 m apart along the pitch and lines are 11–15 m apart, so anything from 4 to 8 m gives the same lines.
- "Through" means the pass crosses the line *between* two of its players. A pass around the end of a line doesn't count. The gap is the distance between those two players.
- "Behind" and "beyond" are strict: the pass must start in front of every player in the line and end behind every one.
- Only SPADL `pass` actions count. Positions come from the snapshot at the start of the pass.
- Difficulty is 0 for a gap of 20 m or more, rising to 1 at 6 m or less, judged at the narrowest gap. Each extra line broken adds 0.2, up to 1. The evidence holds the lines broken and the narrowest gap.
**Why:** the plan's rule left these open, and the planted moments in T13 need a difficulty that rises reliably as the gap narrows.
**Affects:** T13's template must make each difficulty level's gap narrower than the last; a decoy option alone doesn't change the detected difficulty.

**How often it fires.** In simulated play there are about 205 per match, 29% of completed passes. Most break one line through a gap of about 8–13 m, and 1 in 6 breaks two. FIFA's match data counts line breaks through, around *and over* a line, and the best team at one recent tournament made 59 *midfield* line breaks per 90 minutes. So our count is the right order of magnitude but probably high. The simulator's lines are perfectly flat and evenly spaced, so short passes of 9–13 m between two level midfielders count. That's correct by the definition but makes weaker teaching examples. StatsBomb's free data includes player positions ("360" freeze frames) only for other competitions, such as the 2022 men's World Cup, so the count isn't checked against real matches yet.

## T12 — Counter-press detector (2026-10-07)
**Plan said:** a team counter-presses when it regains possession within 5 s of losing it, in the opponent's half. Module `concepts/pressing.py`.
**We did:** as planned, except that the module is `concepts/counter_press.py` and the concept `ConceptId.COUNTER_PRESS` (`counter_press`), because "pressing" alone also covers pressing a goal kick or a slow build-up. These choices are written into the detector's docstring:
- Possessions come from `schema/possession.py`. The 5 s run from the opponent's first action (the one that wins the ball) to the team's first action of its next possession. Losing the ball and winning it back must happen in the same period.
- Both turnovers must happen in open play. A possession that starts with a set piece (throw-in, free kick, corner, goal kick, penalty) doesn't count, and nor does the kickoff after a goal. A kickoff is a plain SPADL pass, so the detector checks whether the team's last action before it was a goal instead. Without this, a team that wins a throw-in deep in the opponent's half 4 s after the opponent's pass goes out would be "counter-pressing".
- "In the opponent's half" is where the winning-back action starts.
- No difficulty is given. The tag's key action is the one that wins the ball back. Its span starts at the team's last action before it lost the ball. The evidence holds the seconds taken and the distance from goal.
**Why:** the plan's rule left these open.
**Affects:** T14's pressing template must win the ball back in open play, not from a restart.

**How often it fires.** In simulated play there are about 28 per match (15–37 over 30 seeds), with a median of 3.2 s to win the ball back, almost all by interception. On the 40 real matches from the T8 note, converted to SPADL with socceraction's StatsBomb converter, the same rule finds about 46 per match (31–64), with a median of 2.2 s. In 62% of the real ones the opponent had the ball for a single action, such as a header or a miscontrol, before it came straight back. That is a loose ball bouncing between teams rather than a team hunting the ball, and makes a weak teaching example. In the simulator the team that wins the ball always plays it at least once more, so this never happens. Requiring the opponent to make at least two actions would leave about 18 real counter-presses per match, but it would also drop the best ones, where the opponent intercepts and is tackled at once. If this detector ever runs on real data, a better rule would look at how the opponent got the ball: a clearance, a lost header or a bad touch means a loose ball, while an interception, a tackle or a completed pass means control.

## T13 — Planting framework and line-breaking template (2026-10-07)
**Plan said:** `MomentSpec`/`PlantRequest` with an `ordering` option; the planter picks target minutes and the engine hands control to the concept's template when one is due; `PlantedMoment(spec, pause_action_id, answer_action_id, snapshot_action_id)`; level 1 = wide gap with one forward option, 2 = narrower gap, 3 = narrow gap plus a decoy; `btl moments` with an ASCII pitch.
**We did:**
- **`ConceptId` moved to `schema/vocab.py`**, where the plan first put it. T10 had put it in `concepts/base.py`, but `Match` now holds planted moments, and `schema/` can't import from `concepts/`.
- **`PlantedMoment`** (`schema/moment.py`) holds the concept, the level, and the pause and answer action ids. There is no separate snapshot id: the learner's picture is always the snapshot at the start of the answer action. `Match.planted` holds them, and `meta.json` saves them, so the saved schema version is now 2 and older saves must be simulated again.
- **The engine never imports `plant/`.** Before each possession it asks an optional `Director` (`sim/script.py`) whether to write the possession's opening instead. The planter is that director. Play then carries on from the scripted opening through the new `play_on` in `chain.py`. A test checks that nothing in `sim/` imports `plant/`.
- **Planting has its own random stream**, a third one spawned from the match seed. Matches without planting are unchanged, and a planted match is identical to the unplanted one up to its first moment.
- **No `ordering` option.** Moments always happen easiest first, which is the only order the plan used.
- **When and where.** Target times are spread evenly over both halves, leaving out each half's first and last 5 minutes. Each moment goes into the first possession on or after its target that starts by winning the ball in open play (an interception or tackle) between 20 and 60 m from the team's own goal line. If the match ends with a moment unplanted, `simulate_with_moments` raises an error. Over 40 seeds that never happened.
- **The template**, in the attacking team's direction: the ball is won, laid off up to 6 m back and 6–12 m infield to a midfielder, and the midfielder passes through the opponent's midfield line. Play pauses after the lay-off. The template writes the answer's snapshot itself. It starts from the shape model's positions around the midfielder without jitter, slides the defending block so its midfield line stands 7 m in front of the passer, and spreads the line around a gap. The pass ends 7 m beyond the line, well short of the back line. Everyone except the passer, the receiver, the decoy and the two players either side of the gap gets 0.5 m of jitter.
- **Levels.** The gap is 18 m, 12 m and 7 m, which the line-breaking detector scores 0.14, 0.57 and 0.93. Level 3 adds a teammate free 12 m to the side as the decoy. Level 1 doesn't limit the forward options, because the gap alone already orders the levels and the extra rule wouldn't change what the detector sees.
- **`btl simulate --plant line_breaking_pass:1,2,3`**, repeatable for more concepts. **`btl moments <match>`** shows each moment's events, the pitch at the answer with the team on the ball attacking left to right, and what the detector found there.
**Why:** keeping `sim/` free of `plant/`, as section 2 of the plan wants, and the open choices in the plan's sketch.
**Affects:** T14's counter-press template. A `Script` writes the opening of one possession, but a counter-press spans three: the team loses the ball, the opponent has it, and the team wins it back. T14 will need either a script that ends its possession with a handover, or one that covers several possessions. T15 regenerates the sample match with planted moments.

## T14 — Counter-press template and counter-attack detector (2026-10-07)
**Plan said:** a pressing template with a planted-means-detected test; a counter-attack detector where a possession won in a team's own half reaches the opposition box within 12 s, with fixtures for 9 s (yes), 15 s (no) and a win in the opponent's half (no). Cuttable.
**We did:**
- **Counter-attack detector** (`concepts/counter_attack.py`, `ConceptId.COUNTER_ATTACK`), as planned. "Won" means the possession starts in open play: not with a set piece, nor with the kickoff after a goal. "Reaches the box" means one of the team's own actions in that possession starts in the penalty area, so a cross that is cleared first doesn't count. The key action is the win, and the span runs to the first action in the box. No difficulty is given.
- **The open-play turnover rule moved** from `concepts/counter_press.py` to `schema/possession.py` (`changes_hands_in_open_play`), because both detectors use it.
- **Counter-press template.** It scripts the *opponent's* possession, starting when the opponent wins the ball in open play 15–40 m from its own goal. The opponent then plays short, quick passes (5–10 m, 0.3–0.7 s between touches) and never takes the ball past 44 m. Its pass is cut out at level 1 straight away, at level 2 after one pass, and at level 3 after two. Over 40 seeds the ball was won back in 0.9–1.8 s, 1.9–2.8 s and 2.6–3.8 s, and the detector found every one. A longer spell on the ball makes the press harder to recognise, which is what the levels stand for. The detector gives no difficulty, so there is no ordering test for these, only a planted-means-detected test.
- **Scripts can now hand the ball over.** `Script.then` is either `PlayOn` (play carries on, as for line-breaking moments) or the `Start` of the other team's possession. The counter-press script ends by handing the ball back with an interception, so its answer, the regain, is the first action of the pressing team's next possession, which the engine simulates as usual. The engine marks every action from the script's first step to the answer with the moment's id.
- **The learner's picture is now the snapshot after the pause action**, not the answer's. For a line-breaking moment they are the same action. For a counter-press, play pauses just after the ball is lost, and the picture shows the opponent on the ball with the pressing team around it. `btl moments` and `docs/event-schema.md` follow this.
- `btl moments` no longer prints "difficulty None" for detectors without a difficulty.

**How often it fires.** Simulated matches have about 0.9 counter-attacks each (0–3 over 30 seeds). On the 40 real matches from the T8 note, converted to SPADL with socceraction, the same rule finds about 3.0 per match (0–7). StatsBomb's analysts mark about 3.9 possessions per match as coming from a counter, though not all of those reach the box. So the simulator plays fewer fast breaks than real teams. There's no band for this yet. The median time to the box is about 10 s in both.
**Why:** the plan left the counter-press template's levels and the details of both rules open, and a counter-press spans three possessions, which the T13 script couldn't express.
**Affects:** T15's sample match can plant both concepts.

## T15 — Milestone 1 wrap-up (2026-10-07)
**Plan said:** `btl inspect <match>` combines events, xT and tags; a README walkthrough; `backend/examples/sample-match/`, about 100 KB, regenerated and committed; setup.md audited from a clean checkout.
**We did:**
- **`btl inspect`** shows each team's goals, shots, passes and completion, possessions, threat added (with a model) and tags per concept, then the events table with a threat column and a concepts column. The concepts column names every tag whose key action is that event, and marks planted ones. `--concept` shows only events with that concept; `--start` and `--count` work as in `btl events`. `events_table` now takes the events to show rather than a start and a count, so `inspect` can pass a filtered list.
- **The sample match is `backend/examples/match-0007`**, not `sample-match`, so that one `btl simulate ... --out examples` command regenerates it in place. It is seed 7 with three line-breaking and three counter-press moments, all six found by their detectors. A test loads it and checks that.
- **It is about 800 KB** (positions 710 KB, events 100 KB). Storing positions to the nearest 10 cm as 32-bit floats would have brought it to about 160 KB, but Lily chose to commit it exact: rounding every save would let a reloaded match differ slightly from the simulated one, and a detector could disagree on a borderline case.
- **setup.md audit.** A fresh clone, with its own virtual environment, passed every step: tests (with the two real-name tests skipped, as documented), ruff, pyright and `btl --help`. No step was missing. Python 3.11 was already installed by uv on this machine, so `uv python install 3.11` itself was not tested from scratch.
- The README now has a walkthrough built on the sample match, and the status table marks the milestone done.
- **`btl matches [folder]`**, not in the plan, lists the saved matches in a folder (by default `data/matches`): clubs, score, seed, number of events and planted moments. Saves from an older schema version are listed underneath with a note to simulate them again, instead of stopping the command. Lily asked for it.
- `btl --help` ends with four example commands, and the commands that read a match show it as `MATCH`, with example folders and a pointer to `btl matches`. Lily hadn't seen from the help that `inspect` needs a match's folder.
- Count messages now use the singular for one ("1 planted moment"), and concept counts are shown as tallies ("switch of play 12"), because concept names don't pluralise by adding an "s".
**Why:** a regeneration command that needs no renaming, and exact positions over a smaller file.
**Affects:** each regeneration adds about 800 KB to the repo's history, so it's worth doing only at milestone ends or when the README's output goes wrong.

## T15 stretch — Animated replay (2026-10-07)
**Plan said:** nothing; the T15 wrap-up listed the replay as a stretch goal, if time allowed.
**We did:**
- **`btl replay MATCH --moment N`** plays the 15 s before a planted moment (`--seconds` changes it) on the same ASCII pitch as `btl moments`, at 10 frames a second (`--speed` scales it). It pauses on the question picture and asks "What happens next?". After Enter, it plays the answer, holds a still of the answer with its full path and `*` target, and lists the events and what the detector found. `--no-reveal` stops at the question. When the output isn't a terminal (piped, or in tests), it prints only the question picture and never waits for input.
- **One direction for the whole clip.** Detectors see each action from its own team's side, so the pitch would turn round at every turnover. New `seen_by(match, team)` in `frames.py` mirrors the whole match once for one team, the team on the ball at the question. Its players are `o` and `G` throughout, so the paused frame is exactly `btl moments`' picture for the same moment (tested on all six sample moments).
- **Frames** (`btl/replay.py`, pure, no pandas). Between two actions, players move in a straight line from one snapshot to the next, and the ball flies from the action's start to its end in at most 3 s, then waits there. Without the cap, the ball would crawl through the 12–45 s of dead-ball time before a restart. Players with unknown positions are left out.
- **Pass paths.** The ball trails a dotted path from where the action under way started. The question frame shows no path, since the ball is still at its start. The final still shows the answer's whole path.
- `pitch_picture`'s drawing moved into a small shared `_Pitch` grid, and its output is unchanged.
**Why:** it gives the pause-and-predict loop a feel in the terminal before the UI exists. The jitter in the shape model (1.5 m) needed no smoothing: spread over the median 2.6 s between actions, it reads as drift, not flicker.
**Affects:** the UI milestone can reuse `lead_up_frames` and `answer_frames`. Players jump a few metres into a planted moment's scripted positions (up to about 15 m in the sample); smoothing that is left for the UI.

## Code review fixes (2026-10-08)
**Plan said:** each half's first and last 5 minutes hold no moment (T13).   **We did:** the planter only enforced the last 5 minutes. A moment that missed its target in the first half could be planted seconds into the second. It now waits until 5 minutes in. The engine now raises `RuntimeError` if a period ends before a planted moment's answer, instead of leaving the moment's ids pointing at the next period's events. `btl simulate --plant` reports moments that didn't fit as a `--plant` error instead of a traceback.   **Why:** found in a review of the whole milestone.   **Affects:** nothing; the sample matches and every seeded test are unchanged.
