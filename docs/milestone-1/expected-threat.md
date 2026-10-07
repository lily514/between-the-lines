# Expected Threat

How the project puts a number on actions, how the number is learned, and why, on synthetic data, it should be read with care.

## The idea

Some places on the pitch are more dangerous than others. With the ball on the edge of the opponent's box, a team is far more likely to score in the next few moves than with the ball near its own goal. **Expected Threat (xT)** puts a number on that: for each area of the pitch, the chance that a team with the ball there scores soon.

An action that moves the ball is then worth the difference: **threat where it ends − threat where it starts.** A pass from midfield into the box scores well. A safe pass backwards scores slightly below zero. This lets us say which passes and dribbles actually made a team more dangerous, not just which ones were completed.

The method comes from Karun Singh's 2019 article "Introducing Expected Threat (xT)". We use the implementation in socceraction (`socceraction.xthreat`).

## How the grid is learned

The pitch is split into 16 cells along its length and 12 across, so each cell is about 6.6 × 5.7 m. From a set of matches, socceraction counts, for each cell:

- how often a player there **shoots**, and how often those shots score;
- how often a player there **moves the ball** instead (passes, crosses, dribbles), and which cell the successful moves end in.

A cell's threat is then: (chance of shooting × chance a shot scores) + (chance of moving × the average threat of where successful moves end). Each cell's value depends on the others, so it is solved by repeating the update until the numbers stop changing. Our grid settles after about 24 rounds.

Every action is first turned so that its team attacks left to right (towards x = 105), using `to_spadl_frame(match, left_to_right=True)`. Without that, the away team's attacks would count towards the wrong goal.

## Our grid

`btl fit-xt` simulates 200 matches (by default) and fits the grid on all their actions, about 331,000. The matches use the season's fixtures in order, with match seeds drawn from `--seed`, so the same command always gives the same grid. It takes about 10 seconds, mostly simulating.

Values in percent, attacking left to right, rows from the top touchline (y = 68) down:

```
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.4  0.5  0.6  0.9  1.1  1.3  1.2  1.4  1.3
 0.2  0.2  0.2  0.2  0.3  0.3  0.3  0.4  0.5  0.6  0.8  1.1  1.1  1.3  1.2  1.3
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.4  0.5  0.7  0.8  1.0  1.2  1.3  1.7  1.5
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.4  0.5  0.7  0.8  1.0  1.3  1.7  2.2  2.8
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.5  0.6  0.7  0.9  1.1  1.6  2.5  3.7  4.6
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.5  0.5  0.7  0.9  1.3  2.0  3.1  6.9 11.7
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.5  0.6  0.7  1.0  1.2  1.8  3.2  6.9 12.1
 0.2  0.2  0.2  0.3  0.3  0.3  0.4  0.5  0.5  0.7  0.9  1.1  1.7  2.5  4.1  3.8
 0.2  0.2  0.2  0.3  0.3  0.3  0.4  0.5  0.6  0.7  0.9  1.0  1.6  2.0  2.6  2.9
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.5  0.6  0.7  0.8  1.1  1.2  1.6  1.8  2.0
 0.2  0.2  0.2  0.3  0.3  0.3  0.4  0.5  0.5  0.7  0.9  1.1  1.3  1.4  1.5  1.7
 0.2  0.2  0.2  0.2  0.3  0.3  0.4  0.4  0.5  0.7  0.9  1.1  1.1  1.4  1.6  1.5
```

The shape is what published grids from real matches look like: almost flat and near zero in a team's own half, rising through midfield, and peaking in the cells right in front of goal (about 12%). That's a sanity check on the simulator as much as on the fit.

The model is saved as JSON at `backend/data/models/expected-threat.json` (gitignored). The file holds the grid and what it was fitted on: number of matches, seed, league seed, and number of actions. socceraction's own `save_model` writes only the bare grid, so the file format is ours (see `btl/io.py`). It is not committed, because it would quietly go stale whenever the simulator changes.

## What gets a value

`rate_match` gives a value only to **successful passes, crosses and dribbles**. Everything else gets none, and shows as a blank in `btl events`:

- **Failed moves.** Losing the ball doesn't show as negative threat. xT measures where the ball went, not the risk taken.
- **Shots.** Their value is the goal (or not), not a move.
- **Restarts.** socceraction counts only `pass`, `cross` and `dribble` as moves, so throw-ins, goal kicks and corners are left out both when fitting and when rating. Kickoffs are SPADL `pass`es, so they are included.
- **Defensive actions** (tackles, interceptions, keeper actions).

## Caveats

- **On synthetic data, xT is circular.** The grid is learned from the simulator, so it can only rediscover the simulator's own rules. For example, the chance of scoring from a cell comes from the shot model in `sim/params.py`, a simple function of distance and angle. The grid is useful for comparing actions *within* our matches, and for teaching what "dangerous" means. It says nothing new about real football.
- **The grid is coarse.** A pass within one 6.6 m cell is worth exactly 0. socceraction's option to smooth the grid is broken with current SciPy (see the T2 note), so we use the plain cells.
- **Values are small.** Most moves change threat by less than 0.01, so `btl events` shows three decimals and prints anything that rounds to zero as a plain `0.000`.
