// Offside: the attacker runs on from where they stood when the ball was played; the line, the margin and the call.
import { endOf, firstWord, ref, upper } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

const RUN_FROM = 0.1
const RUN_TO = 0.6
const CALL_AT = 0.66

/** The attacker the call is about: the player the ball went to, nearest where it arrived. */
const attacker = (scene: SceneData) => {
	const [x, y] = endOf(scene)
	return [...scene.markers]
		.filter(marker => marker.side === 'attacking' && marker.role !== 'on the ball')
		.sort((a, b) => Math.hypot(a.x - x, a.y - y) - Math.hypot(b.x - x, b.y - y))[0]
}

const line = (scene: SceneData): number => scene.line ?? 0

const run = (scene: SceneData): SceneItem[] => {
	const runner = attacker(scene)
	if (runner === undefined) return []
	const [x, y] = endOf(scene)
	return [{ kind: 'move', marker: ref(runner), by: [x - runner.x, y - runner.y], from: RUN_FROM, to: RUN_TO }]
}

const flag = (): SceneItem[] => [
	{ kind: 'flag', up: false, until: CALL_AT - 0.05 },
	{ kind: 'flag', up: true, beat: CALL_AT - 0.05 }
]

const call = (scene: SceneData): SceneItem => ({
	kind: 'word',
	text: '{OFFSIDE_CALL}',
	at: [line(scene) + 4.5, Math.min(60, (attacker(scene)?.y ?? 34) + 14)],
	beat: CALL_AT
})

const margin = (scene: SceneData): SceneItem[] => {
	const runner = attacker(scene)
	if (runner === undefined) return []
	const side = upper(firstWord(scene.facts.beyond_or_behind ?? ''))
	const from: Point = [runner.x, runner.y]
	const to: Point = [line(scene), runner.y]
	return [{ kind: 'bracket', from, to, label: `{margin_m} m ${side}`, beat: 0.25 }]
}

const spec: SceneSpec = {
	concept: 'offside',
	still: 'end',
	focus: scene => [
		[line(scene), 34],
		[105, 34]
	],
	layers: {
		getting_there: scene => [
			{ kind: 'wall', x: line(scene), depth: 3.4 },
			{ kind: 'zone', from: [line(scene), 0], to: [105, 68], fill: true, beat: 0.3 },
			...run(scene),
			...flag(),
			call(scene)
		],
		solid: scene => [
			{ kind: 'line', x: line(scene), label: 'SECOND-LAST DEFENDER', beat: 0.08 },
			...margin(scene),
			...run(scene),
			...flag(),
			call(scene)
		],
		sharp: scene => {
			const runner = attacker(scene)
			return [
				{ kind: 'line', x: line(scene), label: 'SECOND-LAST DEFENDER', beat: 0.08 },
				...(runner === undefined
					? []
					: [{ kind: 'ghost' as const, marker: ref(runner), label: 'WHEN PLAYED', beat: RUN_FROM }]),
				...margin(scene),
				...run(scene),
				...flag(),
				call(scene),
				{ kind: 'edge-label', text: 'JUDGED AT THE PASS, NOT ON ARRIVAL', edge: 'bottom', beat: 0.5 }
			]
		}
	}
}

export default spec
