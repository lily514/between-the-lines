// Shots and goals: the chance, the shot, where it was from and what came of it.
import { at, beatOf, endOf, touchOf } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

/** The boxes at the goal the team attacks, in picture metres. */
const SIX_YARD = { from: [99.5, 24.84] as const, to: [105, 43.16] as const }
const PENALTY_AREA = { from: [88.5, 13.84] as const, to: [105, 54.16] as const }
const GOAL_CENTRE: Point = [105, 34]

const shot = (scene: SceneData): { at: Point; beat: number } => {
	const i = touchOf(scene, 'shot')
	const touch = scene.touches[i]
	return { at: touch === undefined ? endOf(scene) : at(touch), beat: scene.beats[i] ?? 0.5 }
}

/** The box the shot was from, to outline; none from outside the area. */
const zoneOf = (scene: SceneData): SceneItem[] => {
	const [x, y] = shot(scene).at
	const inside = (box: { from: readonly [number, number]; to: readonly [number, number] }) =>
		x >= box.from[0] && y >= box.from[1] && y <= box.to[1]
	const box = inside(SIX_YARD) ? SIX_YARD : inside(PENALTY_AREA) ? PENALTY_AREA : null
	if (box === null) return [{ kind: 'label', text: '{SHOT_ZONE}', at: [x - 4, y], beat: shot(scene).beat }]
	return [{ kind: 'zone', from: box.from, to: box.to, label: '{SHOT_ZONE}', beat: shot(scene).beat }]
}

const outcome = (scene: SceneData): SceneItem => ({
	kind: 'word',
	text: '{SHOT_OUTCOME}',
	at: [Math.min(100, endOf(scene)[0] - 5), endOf(scene)[1] + 10],
	beat: (scene.beats.at(-1) ?? 0.75) + 0.03
})

const spec: SceneSpec = {
	concept: 'shots_and_goals',
	still: 'end',
	focus: () => [GOAL_CENTRE],
	layers: {
		getting_there: scene => [outcome(scene)],
		solid: scene => [
			...zoneOf(scene),
			{
				kind: 'bracket',
				from: shot(scene).at,
				to: GOAL_CENTRE,
				label: '{METRES_FROM_GOAL} m',
				beat: shot(scene).beat + 0.04
			},
			outcome(scene)
		],
		sharp: scene => {
			const first = scene.touches[0]
			return [
				...zoneOf(scene),
				...(first === undefined || first.action === 'shot'
					? []
					: [
							{
								kind: 'label' as const,
								text: 'FROM {CHANCE_FROM}',
								at: at(first),
								beat: beatOf(scene, first.action) + 0.02
							}
						]),
				{
					kind: 'bracket',
					from: shot(scene).at,
					to: GOAL_CENTRE,
					label: '{METRES_FROM_GOAL} m',
					beat: shot(scene).beat + 0.04
				},
				outcome(scene),
				{
					kind: 'edge-label',
					text: 'SHOTS {shots} · ON TARGET {shots_on_target} · THEIRS {opp_shots}',
					edge: 'bottom',
					beat: shot(scene).beat
				}
			]
		}
	}
}

export default spec
