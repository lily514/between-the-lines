// What the specs share: finding players, lines and touches in a fixture. Drawing choices only; the numbers shown
// come from the facts.
import type { MarkerRef, Point, SceneData, SceneMarker, SceneTouch, Side } from './types.ts'

/** Players in a line stand within this many metres of each other along the pitch. */
const LINE_GAP = 6

export const ref = (marker: SceneMarker): MarkerRef => ({ side: marker.side, shirt: marker.shirt })

export const at = (touch: SceneTouch): Point => [touch.x, touch.y]

/** The first touch with the action, or the first touch. */
export const touchOf = (scene: SceneData, action: string): number =>
	Math.max(
		0,
		scene.touches.findIndex(touch => touch.action === action)
	)

/** The beat of the first touch with the action. */
export const beatOf = (scene: SceneData, action: string): number => scene.beats[touchOf(scene, action)] ?? 0

/** Where the play ends. */
export const endOf = (scene: SceneData): Point => {
	const last = scene.touches.at(-1)
	return last === undefined ? [0, 0] : at(last)
}

export const outfield = (scene: SceneData, side: Side): SceneMarker[] =>
	scene.markers.filter(marker => marker.side === side && marker.role !== 'keeper')

/** The players of a side nearest a point, nearest first. */
export const nearest = (scene: SceneData, side: Side, point: Point, count: number): SceneMarker[] =>
	[...outfield(scene, side)]
		.sort((a, b) => Math.hypot(a.x - point[0], a.y - point[1]) - Math.hypot(b.x - point[0], b.y - point[1]))
		.slice(0, count)

/** The marker a touch names, if it is in the key frame. */
export const toucher = (scene: SceneData, touch: SceneTouch | undefined): SceneMarker | undefined =>
	touch?.side === undefined
		? undefined
		: scene.markers.find(marker => marker.side === touch.side && marker.shirt === touch.shirt)

/**
 * The defending side's lines along the pitch, as a mean x per line, nearest their goal first: defence, midfield,
 * forwards. Players stand in a line when their x's are within LINE_GAP of the next.
 */
export const defendingLines = (scene: SceneData): number[] => {
	const xs = outfield(scene, 'defending')
		.map(marker => marker.x)
		.sort((a, b) => b - a)
	const lines: number[][] = []
	for (const x of xs) {
		const line = lines.at(-1)
		const previous = line?.at(-1)
		if (line !== undefined && previous !== undefined && previous - x <= LINE_GAP) {
			line.push(x)
		} else {
			lines.push([x])
		}
	}
	return lines.map(line => line.reduce((sum, x) => sum + x, 0) / line.length)
}

/** Where the segment from `from` to `to` crosses picture x, or null if it doesn't. */
export const crossing = (from: Point, to: Point, x: number): Point | null => {
	if ((from[0] - x) * (to[0] - x) > 0 || from[0] === to[0]) return null
	const share = (x - from[0]) / (to[0] - from[0])
	return [x, from[1] + (to[1] - from[1]) * share]
}

/** A point `metres` further from `from` along the line to `to`. */
export const beyond = (from: Point, to: Point, metres: number): Point => {
	const length = Math.hypot(to[0] - from[0], to[1] - from[1]) || 1
	return [to[0] + ((to[0] - from[0]) / length) * metres, to[1] + ((to[1] - from[1]) / length) * metres]
}

/** A point `metres` away from `from`, directly away from `away`. */
export const awayFrom = (from: Point, away: Point, metres: number): Point => beyond(away, from, metres)

export const upper = (text: string) => text.toUpperCase()

/** The first word of a phrase such as "beyond the second-last defender". */
export const firstWord = (text: string) => text.split(' ')[0] ?? text
