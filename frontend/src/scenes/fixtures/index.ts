// The committed scene fixtures, one per active concept, by concept key. `btl scene-fixtures` writes them.
import type { SceneFixture } from '../types.ts'
import counterPress from './counter_press.json'
import foulsAndCards from './fouls_and_cards.json'
import lineBreakingPass from './line_breaking_pass.json'
import offside from './offside.json'
import restarts from './restarts.json'
import shotsAndGoals from './shots_and_goals.json'
import tackles from './tackles.json'
import transitions from './transitions.json'

export const FIXTURES: Record<string, SceneFixture> = Object.fromEntries(
	[counterPress, foulsAndCards, lineBreakingPass, offside, restarts, shotsAndGoals, tackles, transitions].map(
		fixture => [fixture.concept, fixture as unknown as SceneFixture]
	)
)
