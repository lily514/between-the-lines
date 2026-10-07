# Event schema

How a synthetic match is represented, and how it maps onto socceraction's SPADL format. This is a living reference: update it whenever the schema changes.

Verified against socceraction 1.5.3. The behaviour described here is pinned by `backend/tests/value/test_socceraction_contract.py`.

## The pitch and coordinates

- The pitch is **105 × 68 metres**. `x` runs along the length (0 → 105), `y` across the width (0 → 68). The origin is the bottom-left corner.
- **Stored direction:** the home team attacks left → right (towards x = 105) and the away team right → left, in **both** periods. Teams do not switch ends at half-time. This is what socceraction's own converters produce: they record each event from the acting team's point of view, then flip the away team's events.
- **Normalised direction:** Expected Threat and the concept detectors need every action seen as if the acting team attacks left → right. socceraction's `play_left_to_right(actions, home_team_id)` does this by mirroring the away team's coordinates: `x → 105 − x` and `y → 68 − y`. Snapshots of player positions get the same transform. In this codebase the flip happens only in `btl/schema/frames.py`.

## SPADL columns

socceraction validates actions with `SPADLSchema`, which is **strict**: a DataFrame with any extra column is rejected. So our SPADL frame has exactly these columns, and our own fields live in a separate frame keyed by `(game_id, action_id)`.

| Column | Type | Notes |
|---|---|---|
| `game_id` | int | One id per match |
| `original_event_id` | str | Our simulator's event id, e.g. `"g12-e0345"` |
| `action_id` | int | 0 … n−1, the order within the match |
| `period_id` | int | 1 or 2 |
| `time_seconds` | float | Seconds since the start of the period, ≥ 0 |
| `team_id`, `player_id` | int | Fictional league ids |
| `start_x`, `start_y`, `end_x`, `end_y` | float | Metres, within 0–105 × 0–68 |
| `type_id` | int | `ActionType` (below) |
| `result_id` | int | `Result` (below) |
| `bodypart_id` | int | `BodyPart` (below) |

`type_name`, `result_name` and `bodypart_name` are optional in the schema. socceraction's `add_names` adds them for display.

## Vocabularies

Defined as enums in `btl/schema/vocab.py`. The enum value is the SPADL id, and a test checks that they match socceraction's lists exactly.

- **ActionType:** pass, cross, throw_in, freekick_crossed, freekick_short, corner_crossed, corner_short, take_on, foul, tackle, interception, shot, shot_penalty, shot_freekick, keeper_save, keeper_claim, keeper_punch, keeper_pick_up, clearance, bad_touch, non_action, dribble, goalkick. In SPADL, `dribble` means carrying the ball, not necessarily beating a player.
- **Result:** fail, success, offside, owngoal, yellow_card, red_card. For a shot, `success` means a goal.
- **BodyPart:** foot, head, other, head/other, foot_left, foot_right.

## Extension fields

Kept outside the SPADL frame because the schema is strict:

- `possession_id: int`
- `phase`: open play, set piece, or transition. In simulated matches, a set piece is the action that restarts play: a kickoff (SPADL type `pass`), `throw_in`, `goalkick`, `corner_crossed` or `corner_short`. Transition covers the action that wins the ball in open play and anything that team does in the next 8 seconds, unless play stops first. Everything else is open play.
- `planted_moment_id: int | None`

## Snapshots

The positions of the tracked players at the start of an action.

- **In code** (`btl/schema/snapshot.py`), a match stores them as one `Positions` array of shape `(actions, players, 2)`, indexed by action id, plus a `PlayerSlot` for each column (player, team, goalkeeper or not). `NaN` means a position is unknown, so a data source can give partial snapshots, or none at all for some actions. The simulator tracks all 22 players at every event. `Match.snapshot(action_id)` builds a readable `Snapshot` for one moment, marking the player on the ball.
- **As a frame** (`to_snapshot_frame`), each row is `game_id, action_id, player_id, team_id, x, y, is_actor, is_goalkeeper`, in the same direction as the events. Unknown positions are left out.

## Possessions

SPADL has no possession column, so `btl/schema/possession.py` derives possessions from the events. It ignores the simulator's own `possession_id`, so anything built on it also works for data the simulator didn't produce.

- A possession is an unbroken spell on the ball by one team.
- A new possession starts at the start of each period, and whenever the other team makes an action that **wins the ball**.
- These actions by the other team do *not* win the ball, so they stay inside the current possession: fouls, and failed defensive actions (tackle, interception, clearance, and the goalkeeper actions).

## Concept tags

Concept detectors (`btl/concepts/`) label events with football ideas. Their output is a separate list of tags, never extra SPADL columns:

| Field | Meaning |
|---|---|
| `concept` | Which idea, e.g. `switch_of_play` (`ConceptId`) |
| `game_id`, `action_id` | The match, and the key action |
| `span` | The first and last action involved |
| `difficulty` | 0 (easy to spot) to 1, when the detector defines it |
| `evidence` | The measurements behind the tag, e.g. `{"across (m)": 41.2}` |

Detectors see every action, and its snapshot, as if its team attacks left to right (`to_left_to_right` in `frames.py`). They take possessions from `split_possessions`, never from `possession_id`. Each concept's definition is written in its detector's docstring.

## Expected Threat notes

- `ExpectedThreat.fit` uses actions exactly as given, so they must be normalised left → right first.
- `rate` gives a value only to **successful passes, crosses and dribbles**. Every other action gets `NaN`.
- The default grid is 16 × 12 cells. Internally, row 0 of the grid is the **top** of the pitch (y = 68).
- `rate(..., use_interpolation=True)` doesn't work: it relies on `scipy.interpolate.interp2d`, which SciPy 1.14 removed. We use the plain grid.
