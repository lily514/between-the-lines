# Between the Lines — front-end handoff

You are building the viewer-facing web app for **Between the Lines**, an adaptive learning companion that runs beside a (synthetic) football match on a second screen. It occasionally asks the viewer a question about a key moment, explains the answer at the viewer's level, and tracks their understanding concept by concept.

This file is the spec. `tokens.css` holds every colour, type, spacing and motion value. `design/` holds the approved mockups as reference markup (see "Reading the design files").

---

## 1. Hard constraints

- **Plain HTML, CSS, JavaScript and inline SVG.** No framework, no build step required. ES modules are fine.
- **Mobile first** (390 px reference width), then a desktop **side panel** (400–440 px) beside the viewer's own stream. The panel never covers the stream.
- **Light and dark themes** from `tokens.css`. Dark is the default; honour `prefers-color-scheme` and a manual override (`<html data-theme="light|dark">`).
- **Fictional clubs only:** Northbridge (home) and Westmere (away). No real club names, crests or Premier League branding. No betting look or language (no odds, tickers, "picks").
- **Accessible:** colour is never the only signal (icons + words on every state), WCAG AA text contrast (all token pairs already pass), real `<button>`/`<input>`/`<label>` elements, keyboard operable, screen-reader labelled, `prefers-reduced-motion` respected.
- **Every number has a source.** The UI never invents or computes a stat for display copy; numbers come from the evidence pack / learner model and render in `--font-data` (JetBrains Mono).

## 2. Design principles (the "why" behind the rules)

1. **Respect the match.** Quiet by default. 2–4 live questions per match, plus up to 2 at halftime and 2 at full time. Questions can be turned off.
2. **Never interrupt a transition.** Live questions only in settled possession. Moments from fast play are saved for the next dead ball, halftime or full time.
3. **Think first, then explain.** The viewer commits ("Lock in") before any explanation appears.
4. **Every number has a source** (see above).
5. **Football, not school.** Scouting-report and pundit language. No grades, streak flames, confetti or badges. Wrong answers are treated as interesting, never alarming.

## 3. Colour roles (read this before using tokens)

| Role | Dark | Light | Used for |
|---|---|---|---|
| `--act` | sky blue `#9CC8F0` | maroon `#8C2440` | Anything tappable or chosen: primary buttons, selected answer border + radio dot, focus ring, links, saved-question chip icon |
| `--know` | butter `#F2CF6E` | deep blue `#2F5E8C` | The viewer's understanding: correct-answer tile + ✓, verdict circle, progress bars, the learner-model % after "→", radar "now" polygon, mastered cards, frontier box, scout's-note heading |
| `--incorrect` | = `--text-muted` | = `--text-muted` | Wrong pick: **dashed** border + ✕ icon + "Your pick" label. No red. |
| `--note` | apricot | brown | "Common mix-up" label and ⚠ icon only |
| Pitch | `--pitch`, `--home`, `--away`, `--on-pitch` | **same** | The pitch is bottle green in both themes. Northbridge = filled cream disc with number; Westmere = hollow apricot ring. Option arrows, A/B/C tags, carrier halo and the real ball path use `--on-pitch` (blue). |

Teams are told apart by **shape** (filled disc vs ring), not hue.

## 4. Type, spacing, motion

All values are tokens in `tokens.css`.

- Bricolage Grotesque (display: score, prompts, headings, answer letters), DM Sans (everything readable), JetBrains Mono (times, scores in data rows, every stat). Load from Google Fonts:
  `https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500&display=swap`
- Minimum text 13 px; main reading text 17–19 px (arm's-length second screen).
- Labels/chips: 14 px, 700, uppercase, `letter-spacing: .08em`.
- 4-pt spacing scale; touch targets ≥ 44 px; answer tiles 112 px tall; primary buttons 54 px.
- Motion: hover 120 ms; sheet in 240 ms `--ease-out`; reveal draws the ball path over 600 ms then fades copy in. Reduced motion: no sliding or path drawing, 120 ms crossfade only.

## 5. The pitch (SVG)

- One reusable `renderPitch(svgEl, snapshot, options)` module. Portrait, attacking **up**.
- `viewBox="-3 -3 74 111"`; **units are metres**. Data coordinates are 105 × 68 with the home side attacking +x, so map **`X = y`, `Y = 105 − x`**.
- Markings: outline, halfway, centre circle r 9.15, boxes 40.32 × 16.5, six-yard 18.32 × 5.5. Stroke `--pitch-line`, width 0.4. Flat fill, no stripes.
- Players: home disc r 2.2 (`--home`, number in `--home-ink`, font-size 2.4, display font 700); away ring r 1.8, stroke 0.65 `--away`, fill `--pitch`. Ball r 0.95 white with 0.35 dark stroke, offset ~1.5 m from the carrier.
- Questions **crop the viewBox** to the moment (e.g. `-3 14 74 70`); never scale players. Non-involved players drop to 35–55 % opacity.
- Options: dashed lines (0.6, dash 1.2/1) with arrow markers from carrier to receiver, lettered tag circles r 2.4 near the line midpoint (offset perpendicular to avoid players), carrier halo r 3.8.
- Reveal: real path solid 0.9; receiver's run dashed in `--home`; defensive lines drawn as dashed `--away` horizontals at the mean Y of that line's players, labelled at the right edge; numbered badges (1, 2) where the path crosses each broken line.
- Analyst xT grid: 6 columns × 8.75 m rows, fill `rgba(var(--threat), α)` with α scaled to cell value; start and end cells outlined, values printed in mono.

### Data mapping (from `events.parquet` / `positions.parquet` / `meta.json`)

- Home team id 7 = **Northbridge**, away team id 2 = **Westmere**. Coordinates are absolute (no switching at halftime).
- Shirt number = `player_id % 100`.
- Match clock = `period_id == 1 ? time_seconds : 2700 + time_seconds`, shown `mm:ss`.
- `phase` ∈ `open_play | transition | set_piece`. Live questions only when `open_play` and the possession is ≥ 8 s old with ≥ 4 passes, and never within 6 s of a turnover.
- Lines broken = number of opposition line means (forwards 16–17, midfield 10–13, defenders 3–6 by `player_id % 100`) strictly between pass start x and end x.

## 6. Screens (see `design/` for each)

| # | Screen | File | Notes |
|---|---|---|---|
| 1 | Live companion | `S1-Live` | Score + clock header, full portrait pitch, phase pill (Settled possession / Transition / Dead ball, each with its own icon), saved-question chip, latest caption (`aria-live="polite"`), one older note, "Earlier notes", "Questions: Normal" |
| 2 | Live predict | `S2-Predict` | "Your read" chip, prompt, cropped freeze-frame with A/B/C, 3-column answer tiles (radiogroup), "Save for the break", "Lock in X" |
| 3 | Review at a break | `S3-Review`, `S3-Reveal` | Context line ("Earlier, at 34:18…"), the pass already made (no lines shown), None/One/Two, disabled lock-in until picked, auto-defers to halftime if play restarts. Reveal draws the lines and marks broken ones |
| 4 | Feedback | `S4-Feedback`, `S4-MixUp` | Verdict, reveal pitch, explanation, stat tiles (mono), source line, learner sentence ("Line-breaking passes: 51% → 76%. That's two right in a row.") + bar with 80/95 marks, Simpler / Deeper. Mix-up variant adds the "Common mix-up" aside |
| 5 | Same moment, three levels | `S5-Newcomer`, `S5-Fan`, `S5-Analyst` | Not just word count: newcomer = no numbers, defenders as shaded "walls"; fan = named + numbered lines; analyst = xT grid, evidence table, BKT readout |
| 6 | Scouting reports | `S6-Halftime`, `S6-Fulltime` | Score, stats, radar (4 strands, kickoff dashed vs now solid), scout's note, in progress / mastered, up to 2 review cards, full-time adds goal timeline and recap |
| 7 | Onboarding | `S7-Welcome`, `S7-Placement`, `S7-Result` | 4-option self-assessment → 3 placement checks → starting tier per strand. Under a minute |
| 8 | Preferences | `S8-Preferences` | Questions off/rarely/normal, explanation level (Auto/Newcomer/Fan/Analyst), your team (links to the picker, §14), player focus (switch + select), language, theme, gentle buzz |
| — | Curriculum map | `CM-A-Pitch`, `CM-B-Journey`, `CM-C-Tree` | Three options, still to be chosen (see §10) |
| — | Desktop | `D-Live`, `D-Halftime` | Side panel with keyboard hints; halftime report may take the full window |
| — | Light theme refs | `L-Live`, `L-Feedback` | Reference renders of the light tokens |
| — | System | `Components`, `StyleSheet` | All component states and the token sheet |

## 7. Components and states

Build these as small functions that return DOM (or template strings) and accept a theme-agnostic props object.

- **Answer tile** (`<button role="radio">` inside `role="radiogroup"`): default, hover (`--surface-raised`, `--border-strong`), keyboard focus (3 px `--act` outline, 2 px offset), selected (2 px `--act` border, `--selected` fill, filled radio dot), correct (2 px `--know` border, `--know-tint` fill, ✓ + "Answer"), incorrect (2 px **dashed** `--incorrect`, ✕ + "Your pick"), not-chosen-after-reveal (muted text, faint border).
- **Lock-in button:** disabled (dashed border, muted text, `aria-disabled`), enabled (`--act` fill), pressed (`--act-pressed`).
- **Saved-question chip:** hidden at 0; "1 for the break" / "2 for the break"; "Saved for the break" (1.2 s, border fades in once); "Dead ball · 1 question" (`--act` fill); "Waiting for halftime" (clock icon); "Questions off" (dashed, struck bookmark). Count changes are announced politely.
- **Phase pill:** Settled possession (pulse-line icon), Transition (two arrows), Dead ball (square), "Your read?" (`--act` fill, 4 s when a live question is offered).
- **Verdict mark:** correct = filled `--know` circle with ✓; incorrect = dashed circle with ✕; mix-up = ⚠ in `--note`.
- **Radar:** 4 axes (Possession up, Pressure right, Chances down, Game flow left), rings at 25/50/75/100 in `--border`, kickoff dashed `--text-muted` no fill, now solid 2.5 px `--know` with 16–18 % fill and 4 px nodes, values in mono. Add a visually hidden table with the same values.
- **Progress bar:** track `--surface-raised`, prior part `--know-dim`, gain `--know`; tick at 80 (unlock) solid, 95 (mastery) dashed.

## 8. Interactions and timing

1. Engine offers a live question → one soft haptic (if enabled) → phase pill becomes "Your read?" for 4 s. Nothing covers the pitch yet.
2. Tap the pill → sheet slides up 240 ms; pitch crops/zooms to the moment; focus moves to the question heading.
3. Ignored for 12 s → folds into the saved chip. No penalty.
4. ✕, "Save for the break", swipe down and Esc all **save**, never discard. Focus returns to the saved chip.
5. Lock in disabled until a pick. After lock-in: draw the real path (600 ms), then fade in verdict + copy.
6. Dead ball: at most one saved question, only if that restart type is usually ≥ 20 s away; re-saves if play restarts. Halftime/full time: up to two, always skippable; the report reads fine without them.
7. Desktop keys: 1/2/3 or arrows to pick, Enter to lock in, Esc to save for later, S/D for Simpler/Deeper. No global key handlers outside the open sheet.

## 9. Content rules

- Copy sits at the viewer's level per concept (`beginner`/`intermediate`/`analyst` anchors in `concept_map.yaml`). The Tutor may rephrase anchors but never writes numbers; placeholders `{like_this}` are filled from the evidence pack.
- Tone: warm, confident, brief. Right = "Right read." Wrong = "Good instinct, not this one." plus why.
- Tier names come from the concept map: Newcomer, Casual fan, Engaged fan, Analyst.

## 10. Open items (decide or flag, don't guess)

1. **Curriculum map:** three options in `design/CM-*`. Recommended pairing: A ("Your pitch") in the app, C (tree) in docs/README. Confirm with the owner.
2. **No settled-possession moments are planted** in game 7 (all six are `transition`), so the planter queues every one for a break. The design's live question uses action 996 (58:13). The planter likely needs settled seeds.
3. **`switch_of_play` detector has no concept** in `concept_map.yaml`.
4. **xT values** (0.02 → 0.09) and learner percentages in the mocks are illustrative; wire to `xt_before`/`xt_after` and the BKT state.
5. The desktop and curriculum mocks are dark-only; build them from tokens so light works automatically.

## 11. Reading the design files

`design/*.dc.html` are exported from a design canvas. They are **reference markup, not production code**:

- They load `./support.js` and use `{{t.cXXXXXX}}` template holes. Token keys there are historical hex names (e.g. `cF2CF6E` now resolves to blue in dark). **Ignore the key names; use `tokens.css` roles.** The `themeTokens` object at the bottom of each themed file shows the exact dark/light value per hole.
- Inline styles are exact for layout, size and spacing; translate them into classes using tokens.
- Pitch SVG fragments are copy-ready (they use real coordinates from the sample match).
- `design/canvas.json` holds the board layout and the annotation notes (interaction timing, breaks, three-levels rationale).
- `Main`, `A-*`, `B-*`, `C-*`, `CD-*` are superseded early directions; skip them.

## 12. Suggested build order

1. `tokens.css` + base styles + theme switch.
2. `pitch.js` (mapping, render, crop, options, reveal layers) with a fixture from action 996.
3. Answer tile, lock-in, phase pill, saved chip, verdict, progress bar.
4. Screens 1 → 2 → 4 (live → predict → reveal), then 3, 5, 6, 7, 8.
5. Desktop side panel layout (CSS only; same components).
6. Accessibility pass (keyboard, focus return, `aria-live`, contrast spot check in both themes), reduced-motion pass.

## 13. Done means

- Every screen in §6 renders in dark and light from tokens only (no stray hex in component CSS).
- All interactive elements are reachable and operable by keyboard; focus order matches visual order.
- No state relies on colour alone.
- Pitch positions match the sample data for actions 996 (58:13) and 571 (34:18).
- No real club names, crests, odds or betting terms anywhere.

---

## 14. Addendum: club picker + "Who's playing" team sheet

Design files: `design/TS-Pick`, `TS-Stage1`, `TS-Stage2`, `TS-Stage3`, `TS-Panel-Pick`, `TS-Panel-Stage3` (canvas page "Team sheet + picker"). Same tokens, fonts, pitch and themes as everything else. Phone 390 px and the 420 px desktop side panel (panel = same layout, 20 px gutter).

### 14.1 Pick your team
- One choice from 10 fictional clubs, shown as a `role="radiogroup"` of `<button role="radio">` rows: 3-letter code in a mono outlined box, club name, radio mark. No crests or badges (we only have a name and a code).
- Selected: 2 px `--act` border, `--selected` fill, bold name, filled radio dot. Same pattern as the onboarding self-assessment.
- "Pick one for me" picks a random club other than the current one. Primary button reads "Continue with {club}".
- Clubs in the mock: Calderbrook CAL, Eastholme EAS, Fernhollow Athletic FER, Hexham Anchors HEX, Kestrel Bay KES, Linwood Harbour LIN, Northbridge NOR, Ravensford RAV, Stanmoor STM, Westmere WES. Check names against real clubs before launch.
- Preferences now shows "Your team: {code} {name} · Change" linking here.

### 14.2 Who's playing (before each match)
- Order: **your team first**, then the opponent. Each club is a card: name, code, Home/Away, "filled discs"/"rings", and (stage ≥ 2) formation in mono.
- **Your team highlight:** 2 px `--text` outline + `--surface-raised` fill + a solid "You" tag. On the pitch: dashed outline around your half + a "YOU · {CODE}" label. Never colour alone.
- **Home/away is unchanged:** filled disc = home, ring = away, in the list glyphs and on the pitch. Your team always attacks up the screen (so the home side can be at the top).
- **Key** (always shown): filled disc = home, ring = away, outline + "You" = your team, numbers = shirt numbers.
- Players grouped Goalkeeper / Defenders / Midfielders / Forwards (defenders and midfielders listed left to right). Row: number glyph, name, position in words, one-line description.
- Ends with "Kick off" (primary) and "Not your team? Change it".

### 14.3 Stages (driven by the viewer's best concept level)
| Stage | Adds | Footer note |
|---|---|---|
| 1 (beginner) | List only: number, name, position in words + description | "Get to level 2 in any concept to see the formation." |
| 2 | Formation per club, abbreviation tag (GK, LB, CB, RB, DM, CM, LM, RM, LW, RW, ST), kick-off pitch with both XIs | "Get to level 3 in any concept to see players' numbers from matches you've watched." |
| 3 | Per player 2×2 stat grid: matches watched, passes completed/tried, line-breaking passes, threat added (`--know`) | none |

- Unseen players (no watched matches) show "First time you've seen them" with an eye icon. **Never render zeros for unseen players**; a seen player with a real 0 shows 0.
- Team-level line in stage 3: "From the N matches of theirs you have watched: …" or "You haven't watched {club} yet, so there are no numbers for them."
- No club ratings, strength bars, odds or predictions anywhere.

### 14.4 Data
- Stats come only from matches the viewer has watched (per-viewer history), aggregated per player: `apps`, `passes_completed`, `passes_attempted`, `line_breaking_passes` (completed passes whose end lies beyond the opponent's midfield or defensive line mean, §5), `threat_added` (sum of xT added; the mock values are samples).
- Kick-off shape: positions at the match's first action, mapped so the viewer's team attacks up (`X = 68 − y`, `Y = x` for a team attacking −x; `X = y`, `Y = 105 − x` for +x), spread slightly for legibility.

---

## 15. Addendum: club crests and colours

- Files in `crests/`: `dark/{CODE}.svg`, `light/{CODE}.svg`, `clubs.json` (names, emblems, crest and per-theme colours, contrast), `CREST-COLOURS.md` (table, colour-blind check, rules). Design boards: `design/CR-*` (canvas page "Crests + club colours").
- Clubs: Ripon Wardens RIP (key), Hexham Anchors HEX (anchor), Alnwick Weavers ALN (weaver's shuttle), Bakewell Badgers BAK (badger's head), Truro Otters TRU (otter), Wells Comets WEL (comet), Penrith Sentinels PEN (watchtower), Sherborne Kingfishers SHE (diving kingfisher), Ludlow Ferrymen LUD (chain ferry), Whitby Kestrels WHI (hovering kestrel).
- Shared roundel, primary fill, secondary emblem, theme outline. Inline the SVG or load the theme file; never recolour.
- Crest set is revision 2 (see "Drawing rules" in `CREST-COLOURS.md`). In `design/`, crest images point at `../crests/{dark|light}/{CODE}.svg`.
- Picker rows: 36 px crest + name + code. Team-sheet header: 64 px crests in the match strip, 48 px in each club card, plus a 4 px bar in the club's theme primary. "You" stays outline + tag (§14).
- This list replaces the §14 mock clubs. Northbridge and Westmere (the sample match) are not in it; decide whether to add or rename them.
