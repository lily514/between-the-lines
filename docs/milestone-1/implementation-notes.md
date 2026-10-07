# Milestone 1: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

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
