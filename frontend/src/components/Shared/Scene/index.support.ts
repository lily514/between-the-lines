import type { Band } from '../../../api/client.ts'
import type {
	Beat,
	MarkerRef,
	Point,
	SceneData,
	SceneFixture,
	SceneItem,
	SceneMarker,
	SceneSpec,
	TrackPoint
} from '../../../scenes/types.ts'
import { FULL_VIEW, PITCH_LENGTH, PITCH_WIDTH, toScreen, type ViewBox } from '../Pitch/index.support.ts'

/** The loop: fade in to 6%, the story to 90%, fade out to 100%. The story's beats run 0 to 1 inside it. */
export const LOOP_SECONDS = 5
const STORY_FROM = 6
const STORY_TO = 86
/** The ball waits, then travels, then there is time to read the last labels. */
export const BALL_STARTS = 0.08
export const BALL_ARRIVES = 0.75
/** A long wait in the data (a corner walked to) is shown as a short one. */
const LONGEST_PAUSE = 3
const SHORTEST_PAUSE = 0.4
/** The view: 5 : 4, at least 50 × 40 metres, with room round what it must show. */
export const VIEW_WIDTH = 50
export const VIEW_HEIGHT = 40
const VIEW_MARGIN = 5
/** A player this close to the play is drawn at full strength. */
const INVOLVED_WITHIN = 2.5

/** What a spec gets to draw from. */
export const sceneData = (fixture: SceneFixture): SceneData => ({
	fixture,
	facts: Object.fromEntries(
		Object.entries({ ...fixture.pack.context, ...fixture.pack.outcome }).map(([key, fact]) => [key, fact.display])
	),
	touches: fixture.path,
	beats: beats(fixture.path.map(touch => touch.at)),
	markers: fixture.snapshot.markers,
	line: fixture.pack.reveal_line
})

/** Each touch's story beat: the gaps between touches, long ones shortened, spread from BALL_STARTS to BALL_ARRIVES. */
export const beats = (times: readonly number[]): number[] => {
	const gaps = times
		.slice(1)
		.map((time, i) => Math.min(LONGEST_PAUSE, Math.max(SHORTEST_PAUSE, time - (times[i] ?? 0))))
	const total = gaps.reduce((sum, gap) => sum + gap, 0) || 1
	let elapsed = 0
	return times.map((_, i) => {
		if (i > 0) elapsed += gaps[i - 1] ?? 0
		return round(BALL_STARTS + (BALL_ARRIVES - BALL_STARTS) * (elapsed / total), 3)
	})
}

/**
 * A template over the facts: `GAP {gap_m} m` → `GAP 13 m`, and `{RESTART_TYPE}` → `CORNER`, in capitals. An unknown
 * key is left in braces, so tests catch it.
 */
export const fill = (text: string, facts: Record<string, string>): string =>
	text.replace(/\{([a-zA-Z_]+)\}/g, (whole, key: string) => {
		const value = facts[key.toLowerCase()]
		if (value === undefined) return whole
		return key === key.toUpperCase() ? value.toUpperCase() : value
	})

/** The ball's track: the spec's, or the play's touches. */
export const ballTrack = (spec: SceneSpec, scene: SceneData): TrackPoint[] =>
	spec.track?.(scene) ?? scene.touches.map((touch, i) => ({ beat: scene.beats[i] ?? 0, at: [touch.x, touch.y] }))

/** The items a layer draws, with every text filled from the facts. */
export const layerItems = (spec: SceneSpec, band: Band, scene: SceneData): SceneItem[] =>
	spec.layers[band](scene).map(item => fillItem(item, scene.facts))

const fillItem = (item: SceneItem, facts: Record<string, string>): SceneItem => {
	switch (item.kind) {
		case 'word':
		case 'label':
		case 'edge-label':
		case 'pill':
		case 'badge':
		case 'bracket':
			return { ...item, ...textOf(item, facts) }
		case 'line':
		case 'zone':
		case 'ghost':
			return item.label === undefined ? item : { ...item, label: fill(item.label, facts) }
		default:
			return item
	}
}

const textOf = (item: { text?: string; label?: string }, facts: Record<string, string>) => ({
	...(item.text === undefined ? {} : { text: fill(item.text, facts) }),
	...(item.label === undefined ? {} : { label: fill(item.label, facts) })
})

/** Every template text in a layer, filled: what a test checks for braces left over. */
export const textsOf = (items: readonly SceneItem[]): string[] =>
	items.flatMap(item => {
		const texts: string[] = []
		if ('text' in item) texts.push(item.text)
		if ('label' in item) texts.push(item.label)
		return texts
	})

/** The picture points the view must show: the ball's track, the players in the play, and the spec's focus. */
export const focusPoints = (spec: SceneSpec, scene: SceneData, items: readonly SceneItem[]): Point[] => {
	const track = ballTrack(spec, scene).map(point => point.at)
	const involved = scene.markers
		.filter(marker => isInvolved(marker, track, items))
		.map((marker): Point => [marker.x, marker.y])
	return [...track, ...involved, ...(spec.focus?.(scene) ?? [])]
}

/** Whether a player is drawn at full strength: on the ball, close to the play, moved by the scene or named by it. */
export const isInvolved = (marker: SceneMarker, track: readonly Point[], items: readonly SceneItem[]): boolean => {
	if (marker.role === 'on the ball') return true
	if (track.some(([x, y]) => Math.hypot(marker.x - x, marker.y - y) <= INVOLVED_WITHIN)) return true
	return items.some(
		item =>
			(item.kind === 'move' && same(item.marker, marker)) ||
			(item.kind === 'ghost' && same(item.marker, marker)) ||
			(item.kind === 'involve' && item.markers.some(named => same(named, marker)))
	)
}

export const same = (named: MarkerRef, marker: SceneMarker) =>
	named.side === marker.side && named.shirt === marker.shirt

/** The 5 : 4 view round the screen points, at least 50 × 40, grown to fit and kept on the pitch. */
export const sceneView = (points: readonly Point[]): ViewBox => {
	const screen = points.map(toScreen)
	if (screen.length === 0) return { x: 0, y: 0, width: VIEW_WIDTH, height: VIEW_HEIGHT }
	const xs = screen.map(([x]) => x)
	const ys = screen.map(([, y]) => y)
	const [left, right] = [Math.min(...xs) - VIEW_MARGIN, Math.max(...xs) + VIEW_MARGIN]
	const [top, bottom] = [Math.min(...ys) - VIEW_MARGIN, Math.max(...ys) + VIEW_MARGIN]
	const width = Math.max(VIEW_WIDTH, right - left, ((bottom - top) * VIEW_WIDTH) / VIEW_HEIGHT)
	const height = (width * VIEW_HEIGHT) / VIEW_WIDTH
	const centreX = (left + right) / 2
	const centreY = (top + bottom) / 2
	return {
		x: clamp(centreX - width / 2, FULL_VIEW.x, Math.max(FULL_VIEW.x, FULL_VIEW.x + FULL_VIEW.width - width)),
		y: clamp(centreY - height / 2, FULL_VIEW.y, Math.max(FULL_VIEW.y, FULL_VIEW.y + FULL_VIEW.height - height)),
		width: round(width),
		height: round(height)
	}
}

const clamp = (value: number, low: number, high: number) => round(Math.min(high, Math.max(low, value)))
export const round = (value: number, places = 2) => {
	const scale = 10 ** places
	return Math.round(value * scale) / scale
}

/** A story beat as a percentage of the loop. */
export const percentOf = (beat: Beat) => round(STORY_FROM + (STORY_TO - STORY_FROM) * Math.min(1, Math.max(0, beat)))

/** The keyframes that show something from a beat, and hide it again at `until`. */
export const appearFrames = (name: string, beat: Beat = 0, until?: Beat): string => {
	const from = percentOf(beat)
	if (beat <= 0 && until === undefined) return ''
	const start = beat <= 0 ? '' : `0%,${String(Math.max(0, from - 0.1))}%{opacity:0}`
	if (until === undefined) return `@keyframes ${name}{${start}${String(from)}%,100%{opacity:1}}`
	const to = percentOf(until)
	return `@keyframes ${name}{${start}${String(from)}%,${String(Math.max(from, to - 0.1))}%{opacity:1}${String(to)}%,100%{opacity:0}}`
}

/** The keyframes that carry something along screen offsets at beats, holding each until the next. */
export const travelFrames = (name: string, stops: readonly { beat: Beat; dx: number; dy: number }[]): string => {
	const first = stops[0]
	if (first === undefined) return ''
	const frames = stops.map(
		stop =>
			`${String(percentOf(stop.beat))}%{transform:translate(${String(round(stop.dx))}px,${String(round(stop.dy))}px)}`
	)
	return `@keyframes ${name}{0%,${frames.join('')}${String(percentOf(1))}%,100%{transform:translate(${String(round(stops[stops.length - 1]?.dx ?? 0))}px,${String(round(stops[stops.length - 1]?.dy ?? 0))}px)}}`
}

/** The keyframes of a halo closing in and fading. */
export const haloFrames = (name: string, beat: Beat, until: Beat): string => {
	const from = percentOf(beat)
	const to = percentOf(until)
	const mid = round(from + (to - from) * 0.5)
	return `@keyframes ${name}{0%,${String(from)}%{opacity:0;transform:scale(1.6)}${String(mid)}%{opacity:1;transform:scale(1)}${String(Math.max(mid, to - 0.1))}%{opacity:1;transform:scale(1)}${String(to)}%,100%{opacity:0;transform:scale(1)}}`
}

/** Screen offsets of the ball's track from its first point. */
export const trackStops = (track: readonly TrackPoint[]) => {
	const first = track[0]
	if (first === undefined) return []
	const [x0, y0] = toScreen(first.at)
	return track.map(point => {
		const [x, y] = toScreen(point.at)
		return { beat: point.beat, dx: x - x0, dy: y - y0 }
	})
}

/** A CSS animation shorthand for the loop. */
export const loop = (name: string, easing = 'linear') => `${name} ${String(LOOP_SECONDS)}s ${easing} infinite`

/** The cell of a grid a picture point falls in, as a zone in picture metres. */
export const cellOf = ([x, y]: Point, [along, across]: readonly [number, number]): { from: Point; to: Point } => {
	const length = PITCH_LENGTH / along
	const width = PITCH_WIDTH / across
	const column = Math.min(along - 1, Math.floor(x / length))
	const row = Math.min(across - 1, Math.floor(y / width))
	return { from: [column * length, row * width], to: [(column + 1) * length, (row + 1) * width] }
}

/** Whether an item shows in a still frame: at the start only what is there from the first beat; at the end, all. */
export const shownInStill = (item: SceneItem, still: 'start' | 'end'): boolean => {
	if (!('beat' in item || 'until' in item)) return true
	const beat = item.beat ?? 0
	const until = item.until
	if (still === 'start') return beat <= 0 && (until === undefined || until > 0)
	return until === undefined
}

/** A name CSS keyframes can use, from React's id. */
export const cssName = (id: string, suffix: string) => `scene-${id.replace(/[^a-zA-Z0-9]/g, '')}-${suffix}`
