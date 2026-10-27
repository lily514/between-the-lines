// Transitions and counter-attacks: the ball is won, and the team goes for goal before the defence is back in shape.
import { at, defendingLines, endOf, ref, toucher } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

const PENALTY_AREA = { from: [88.5, 13.84] as const, to: [105, 54.16] as const }

const won = (scene: SceneData): { at: Point; beat: number } => {
	const first = scene.touches[0]
	return { at: first === undefined ? [0, 0] : at(first), beat: scene.beats[0] ?? 0.08 }
}

const arrives = (scene: SceneData) => scene.beats.at(-1) ?? 0.75

/** Each player the ball reaches runs from where they stood to where they take it. */
const runs = (scene: SceneData): SceneItem[] =>
	scene.touches.flatMap((touch, i): SceneItem[] => {
		const player = toucher(scene, touch)
		if (i === 0 || player === undefined || touch.side !== 'attacking') return []
		const by: Point = [touch.x - player.x, touch.y - player.y]
		if (Math.hypot(by[0], by[1]) < 1) return []
		return [{ kind: 'move', marker: ref(player), by, from: won(scene).beat, to: scene.beats[i] ?? 0.5 }]
	})

const box = (scene: SceneData): SceneItem => ({
	kind: 'zone',
	from: PENALTY_AREA.from,
	to: PENALTY_AREA.to,
	fill: true,
	beat: arrives(scene) - 0.02
})

/** A timer from the ball being won to reaching the box. */
const timer = (scene: SceneData): SceneItem[] => {
	const seconds = Math.floor(Number(scene.facts.seconds_to_box ?? 0))
	const from = won(scene).beat
	const to = arrives(scene)
	const step = seconds > 0 ? (to - from) / (seconds + 1) : to - from
	const ticks = Array.from({ length: seconds + 1 }, (_, i): SceneItem => ({
		kind: 'pill',
		text: `${String(i)} s`,
		beat: from + step * i,
		until: from + step * (i + 1)
	}))
	return [...ticks, { kind: 'pill', text: 'IN THE BOX IN {seconds_to_box} s', beat: to }]
}

const spec: SceneSpec = {
	concept: 'transitions',
	still: 'end',
	focus: () => [[PENALTY_AREA.from[0], 34]],
	layers: {
		getting_there: scene => [
			{ kind: 'ring', at: won(scene).at, r: 2.6, beat: won(scene).beat },
			...runs(scene),
			box(scene)
		],
		solid: scene => [
			{ kind: 'ring', at: won(scene).at, r: 2.6, beat: won(scene).beat },
			...runs(scene),
			box(scene),
			...timer(scene),
			{
				kind: 'edge-label',
				text: 'WON {WON_METRES_FROM_OWN_GOAL} m FROM OWN GOAL',
				edge: 'bottom',
				beat: won(scene).beat + 0.05
			}
		],
		sharp: scene => {
			const [line] = defendingLines(scene)
			return [
				...(line === undefined
					? []
					: [{ kind: 'line' as const, x: line, label: 'LAST LINE WHEN WON', beat: won(scene).beat }]),
				{ kind: 'ring', at: won(scene).at, r: 2.6, beat: won(scene).beat },
				...runs(scene),
				box(scene),
				...timer(scene),
				{
					kind: 'label',
					text: 'STRAIGHT FOR GOAL',
					at: [endOf(scene)[0] - 6, endOf(scene)[1]],
					beat: arrives(scene)
				},
				{
					kind: 'edge-label',
					text: 'SHOTS ON THE BREAK {transition_shots} · SETTLED {settled_shots}',
					edge: 'bottom',
					beat: arrives(scene) + 0.02
				}
			]
		}
	}
}

export default spec
