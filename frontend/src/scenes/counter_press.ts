// Counter-pressing: the ball is lost, the pressers close in, and it is won back in seconds.
import { at, awayFrom, beatOf, endOf, nearest, ref, touchOf } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

const PRESS_FROM_RUN = 5

/** Where the ball was lost: the first touch by the other side. */
const lost = (scene: SceneData): { at: Point; beat: number } => {
	const i = Math.max(
		1,
		scene.touches.findIndex(touch => touch.side === 'defending')
	)
	const touch = scene.touches[i] ?? scene.touches[0]
	return { at: touch === undefined ? [0, 0] : at(touch), beat: scene.beats[i] ?? 0.2 }
}

const regained = (scene: SceneData): { at: Point; beat: number } => {
	const i = touchOf(scene, 'tackle')
	const touch = scene.touches[i]
	return { at: touch === undefined ? endOf(scene) : at(touch), beat: scene.beats[i] ?? 0.6 }
}

/** The pressers: as many of the side that lost it as the pack counts, nearest the loss, closing in from further out. */
const pressers = (scene: SceneData): SceneItem[] => {
	const count = { one: 1, two: 2, three: 3, four: 4 }[scene.facts.pressers ?? ''] ?? 2
	const from = lost(scene)
	const to = regained(scene)
	return nearest(scene, 'attacking', from.at, count).map(player => {
		const start = awayFrom([player.x, player.y], from.at, PRESS_FROM_RUN)
		return {
			kind: 'move',
			marker: ref(player),
			by: [player.x - start[0], player.y - start[1]],
			from: from.beat,
			to: to.beat,
			arrive: true
		}
	})
}

const halo = (scene: SceneData): SceneItem => ({
	kind: 'halo',
	at: regained(scene).at,
	beat: lost(scene).beat,
	until: regained(scene).beat + 0.12
})

/** A timer that counts the seconds until the ball is back. */
const timer = (scene: SceneData): SceneItem[] => {
	const seconds = Math.floor(Number(scene.facts.seconds_to_regain ?? 0))
	const from = lost(scene).beat
	const to = regained(scene).beat
	const step = seconds > 0 ? (to - from) / (seconds + 1) : to - from
	const ticks = Array.from({ length: seconds + 1 }, (_, i): SceneItem => ({
		kind: 'pill',
		text: `${String(i)} s`,
		beat: from + step * i,
		until: from + step * (i + 1)
	}))
	return [...ticks, { kind: 'pill', text: 'BACK IN {seconds_to_regain} s', beat: to }]
}

const spec: SceneSpec = {
	concept: 'counter_press',
	still: 'start',
	layers: {
		getting_there: scene => [halo(scene), ...pressers(scene)],
		solid: scene => [
			halo(scene),
			...pressers(scene),
			...timer(scene),
			{ kind: 'edge-label', text: '{PRESSERS} PRESSERS', edge: 'bottom-right', beat: regained(scene).beat }
		],
		sharp: scene => {
			const won = regained(scene).at
			return [
				{
					kind: 'zone',
					from: [Math.max(0, won[0] - 30), 0],
					to: [won[0] - 6, 68],
					fill: true,
					label: 'SPACE BEHIND IF IT FAILS',
					beat: lost(scene).beat
				},
				halo(scene),
				...pressers(scene),
				{
					kind: 'bracket',
					from: won,
					to: [105, won[1]],
					label: '{metres_from_goal} m FROM GOAL',
					beat: regained(scene).beat
				},
				{
					kind: 'edge-label',
					text: '{PRESSERS} PRESSERS',
					edge: 'bottom-right',
					beat: beatOf(scene, 'tackle')
				}
			]
		}
	}
}

export default spec
