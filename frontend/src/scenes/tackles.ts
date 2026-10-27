// Tackles and turnovers: the ball is won, how and where, and why the place matters.
import { at, awayFrom, ref, toucher } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

/** Where the middle and attacking thirds start, in metres from the team's own goal. */
const MIDDLE_FROM = 35
const ATTACKING_FROM = 70
const STEPS_IN = 4

/** The touch that won the ball: the first by the side that ends with it. */
const win = (scene: SceneData): { at: Point; beat: number; index: number } => {
	const i = Math.max(
		0,
		scene.touches.findIndex(touch => touch.side === 'attacking')
	)
	const touch = scene.touches[i]
	return { at: touch === undefined ? [0, 0] : at(touch), beat: scene.beats[i] ?? 0.4, index: i }
}

/** The winner steps in from a few metres away. */
const stepsIn = (scene: SceneData): SceneItem[] => {
	const won = win(scene)
	const winner = toucher(scene, scene.touches[won.index])
	const loser = scene.touches[0]
	if (winner === undefined || loser === undefined) return []
	const start = awayFrom([winner.x, winner.y], at(loser), STEPS_IN)
	return [
		{
			kind: 'move',
			marker: ref(winner),
			by: [winner.x - start[0], winner.y - start[1]],
			from: 0.05,
			to: won.beat,
			arrive: true
		}
	]
}

/** The third the ball was won in, as a zone to shade. */
const third = (scene: SceneData): { from: Point; to: Point } => {
	const x = win(scene).at[0]
	const low = x < MIDDLE_FROM ? 0 : x < ATTACKING_FROM ? MIDDLE_FROM : ATTACKING_FROM
	const high = x < MIDDLE_FROM ? MIDDLE_FROM : x < ATTACKING_FROM ? ATTACKING_FROM : 105
	return { from: [low, 0], to: [high, 68] }
}

const spec: SceneSpec = {
	concept: 'tackles',
	still: 'end',
	focus: scene => [
		[win(scene).at[0], 10],
		[win(scene).at[0], 58]
	],
	layers: {
		getting_there: scene => [
			...stepsIn(scene),
			{ kind: 'halo', at: win(scene).at, r: 4.5, beat: 0.05, until: win(scene).beat + 0.1 },
			{ kind: 'ring', at: win(scene).at, r: 2.6, beat: win(scene).beat },
			{
				kind: 'word',
				text: '{RECOVERY_TYPE}',
				at: [win(scene).at[0] + 5, win(scene).at[1]],
				beat: win(scene).beat + 0.05
			}
		],
		solid: scene => [
			{ kind: 'line', x: MIDDLE_FROM, label: 'MIDDLE THIRD' },
			{ kind: 'line', x: ATTACKING_FROM, label: 'ATTACKING THIRD' },
			{ kind: 'zone', ...third(scene), fill: true, beat: win(scene).beat },
			...stepsIn(scene),
			{ kind: 'ring', at: win(scene).at, r: 2.6, beat: win(scene).beat },
			{
				kind: 'label',
				text: 'WON IN {PITCH_THIRD}',
				at: [win(scene).at[0] + 4.5, win(scene).at[1]],
				beat: win(scene).beat + 0.05
			},
			{
				kind: 'edge-label',
				text: '{METRES_FROM_OWN_GOAL} m FROM OWN GOAL',
				edge: 'bottom',
				beat: win(scene).beat + 0.1
			}
		],
		sharp: scene => [
			{ kind: 'line', x: ATTACKING_FROM, label: 'HIGH' },
			...stepsIn(scene),
			{ kind: 'ring', at: win(scene).at, r: 2.6, beat: win(scene).beat },
			{
				kind: 'zone',
				from: [win(scene).at[0] + 4, 8],
				to: [105, 60],
				fill: true,
				label: 'GROUND STILL TO COVER',
				beat: win(scene).beat + 0.08
			},
			{
				kind: 'label',
				text: '{RECOVERY_TYPE} · {METRES_FROM_OWN_GOAL} m OUT',
				at: [win(scene).at[0] - 4.5, win(scene).at[1]],
				beat: win(scene).beat + 0.04
			},
			{
				kind: 'edge-label',
				text: 'HIGH RECOVERIES {high_recoveries} · USUAL {avg_high_recoveries}',
				edge: 'bottom',
				beat: win(scene).beat + 0.15
			}
		]
	}
}

export default spec
