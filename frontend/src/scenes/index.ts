// The scene specs by concept key. A concept the page can show a scene for has one here and a fixture in `fixtures/`.
import counterPress from './counter_press.ts'
import foulsAndCards from './fouls_and_cards.ts'
import lineBreakingPass from './line_breaking_pass.ts'
import offside from './offside.ts'
import restarts from './restarts.ts'
import type { SceneSpec } from './types.ts'

export const SPECS: Record<string, SceneSpec> = Object.fromEntries(
	[restarts, offside, foulsAndCards, lineBreakingPass, counterPress].map(spec => [spec.concept, spec])
)
