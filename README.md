# Between the Lines

An adaptive learning tool that helps football fans understand the game better over time.

During a match, it pauses at a "teachable moment" and asks you to predict what should happen next, such as *"where should #8 pass?"* Then it reveals the answer, with an explanation pitched at your level. A learner model tracks which football concepts you understand, and the questions get harder as you improve.

All match data is synthetic: a fictional league, fictional clubs, and fictional players.

## Status

Built for the "Inside the Game" hackathon.

| Milestone | Scope | Status |
|---|---|---|
| 1. Data engine | Event schema, match simulator, Expected Threat valuation, concept detectors, CLI | In progress |

Work in progress lives on milestone branches and is merged to `main` when each milestone is complete.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/). Full steps are in [docs/setup.md](docs/setup.md).

```sh
cd backend
uv python install 3.11
uv sync
uv run btl --help
```

Simulate a match and look at its events:

```sh
uv run btl simulate --seed 7
uv run btl events data/matches/match-0007
```

Learn the Expected Threat grid once (about 10 seconds), and `btl events` adds a threat column:

```sh
uv run btl fit-xt
```

List the football concepts the detectors find in a match, such as switches of play:

```sh
uv run btl tags data/matches/match-0007
```

Plant teachable moments, easiest first, and see each one on an ASCII pitch. Here: three line-breaking passes and one counter-press:

```sh
uv run btl simulate --seed 7 --plant line_breaking_pass:1,2,3 --plant counter_press:1
uv run btl moments data/matches/match-0007
```
