// The scene specs by concept key. A concept the page can show a scene for has one here and a fixture in `fixtures/`.
import counterPress from './counter_press.ts'
import foulsAndCards from './fouls_and_cards.ts'
import lineBreakingPass from './line_breaking_pass.ts'
import offside from './offside.ts'
import restarts from './restarts.ts'
import shotsAndGoals from './shots_and_goals.ts'
import tackles from './tackles.ts'
import transitions from './transitions.ts'
import type { SceneSpec } from './types.ts'

export const SPECS: Record<string, SceneSpec> = Object.fromEntries(
	[tackles, shotsAndGoals, restarts, offside, foulsAndCards, transitions, lineBreakingPass, counterPress].map(
		spec => [spec.concept, spec]
	)
)
