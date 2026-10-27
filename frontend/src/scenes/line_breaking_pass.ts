// Line-breaking passes: the defending lines as walls, the gap the pass found, and the threat it added.
import { cellOf } from '../components/Shared/Scene/index.support.ts'
import { at, crossing, defendingLines, endOf } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

const LINE_NAMES = ['DEFENCE', 'MIDFIELD', 'FORWARDS']
/** The threat model's grid: 12 cells along the pitch, 8 across. */
const THREAT_CELLS = [12, 8] as const

const start = (scene: SceneData): Point => {
	const pass = scene.touches[0]
	return pass === undefined ? [0, 0] : at(pass)
}

/** Each defending line, with where and when the pass crosses it (null if it doesn't). */
const lines = (scene: SceneData) => {
	const from = start(scene)
	const to = endOf(scene)
	const first = scene.beats[0] ?? 0
	const last = scene.beats.at(-1) ?? 1
	return defendingLines(scene)
		.slice(0, 2)
		.map((x, i) => {
			const crossed = crossing(from, to, x)
			const share = crossed === null ? null : (crossed[0] - from[0]) / (to[0] - from[0] || 1)
			return {
				x,
				name: LINE_NAMES[i] ?? '',
				crossed,
				beat: share === null ? null : first + (last - first) * share
			}
		})
}

const brokenBadges = (scene: SceneData): SceneItem[] =>
	lines(scene)
		.filter(line => line.crossed !== null)
		.sort((a, b) => (a.beat ?? 0) - (b.beat ?? 0))
		.map((line, i) => ({
			kind: 'badge',
			at: line.crossed ?? [0, 0],
			text: String(i + 1),
			beat: (line.beat ?? 0) + 0.02
		}))

const namedLines = (scene: SceneData): SceneItem[] =>
	lines(scene).map(line => ({ kind: 'line', x: line.x, label: line.name }))

/** The gap between the two nearest lines, measured on the side of the pitch away from the pass. */
const gap = (scene: SceneData): SceneItem[] => {
	const [defence, midfield] = lines(scene)
	if (defence === undefined || midfield === undefined) return []
	const y = start(scene)[1] > 34 ? 10 : 58
	return [{ kind: 'bracket', from: [midfield.x, y], to: [defence.x, y], label: 'GAP {gap_m} m', beat: 0.1 }]
}

const spec: SceneSpec = {
	concept: 'line_breaking_pass',
	still: 'start',
	focus: scene => lines(scene).map(line => [line.x, start(scene)[1]]),
	layers: {
		getting_there: scene => [
			...lines(scene).map((line): SceneItem => ({ kind: 'wall', x: line.x })),
			...lines(scene)
				.filter(line => line.beat !== null)
				.map((line): SceneItem => ({ kind: 'wall', x: line.x, lit: true, beat: (line.beat ?? 0) + 0.02 }))
		],
		solid: scene => [
			...namedLines(scene),
			...gap(scene),
			...brokenBadges(scene),
			{ kind: 'label', text: 'BETWEEN THE LINES', at: [endOf(scene)[0] + 4, endOf(scene)[1]], beat: 0.6 }
		],
		sharp: scene => {
			const from = cellOf(start(scene), THREAT_CELLS)
			const to = cellOf(endOf(scene), THREAT_CELLS)
			return [
				{ kind: 'grid', cells: THREAT_CELLS },
				...namedLines(scene),
				{ kind: 'zone', from: from.from, to: from.to, label: '{xt_before}', beat: 0.04 },
				{ kind: 'zone', from: to.from, to: to.to, label: '{xt_after}', beat: 0.6 },
				...brokenBadges(scene),
				{ kind: 'edge-label', text: 'THREAT PER ZONE · xT', edge: 'bottom-right' }
			]
		}
	}
}

export default spec
