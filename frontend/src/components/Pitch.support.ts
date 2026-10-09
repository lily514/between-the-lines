import type { Marker, Picture } from '../api/client.ts'

/** A point in metres. */
export type Point = readonly [number, number]

export interface ViewBox {
	x: number
	y: number
	width: number
	height: number
}

/** An answer option drawn on the pitch: its letter and where the pass would go, in picture coordinates. */
export interface PitchOption {
	key: string
	at: Point
}

export const PITCH_LENGTH = 105
export const PITCH_WIDTH = 68
const EDGE = 3
/** The whole pitch with a 3 m border, in screen metres. */
export const FULL_VIEW: ViewBox = {
	x: -EDGE,
	y: -EDGE,
	width: PITCH_WIDTH + 2 * EDGE,
	height: PITCH_LENGTH + 2 * EDGE
}
// A cropped view keeps the full width, so players are drawn the same size in every view.
const CROP_MARGIN = 10
const MIN_CROP_HEIGHT = 50
// A marker this close to the ball, a target or the path is part of the moment.
const INVOLVED_WITHIN = 1.5
const BALL_OFFSET = 1.1
const TAG_OFFSET = 2.6

/**
 * Picture coordinates (105 × 68, the team on the ball attacking towards x = 105) to the portrait screen, attacking up.
 *
 * The attacker's left is y = 68, so it lands on the left of the screen.
 */
export const toScreen = ([x, y]: Point): Point => [PITCH_WIDTH - y, PITCH_LENGTH - x]

export const viewBoxText = (view: ViewBox) => [view.x, view.y, view.width, view.height].map(round).join(' ')

/** A view of the full width, cropped top and bottom to the given screen points with a margin. */
export const cropTo = (points: readonly Point[]): ViewBox => {
	if (points.length === 0) {
		return FULL_VIEW
	}
	const ys = points.map(([, y]) => y)
	let top = Math.min(...ys) - CROP_MARGIN
	let bottom = Math.max(...ys) + CROP_MARGIN
	const short = MIN_CROP_HEIGHT - (bottom - top)
	if (short > 0) {
		top -= short / 2
		bottom += short / 2
	}
	const minY = FULL_VIEW.y
	const maxY = FULL_VIEW.y + FULL_VIEW.height
	// Close to a goal line, show it: a view that stops just short of it looks cut off.
	if (top < minY + CROP_MARGIN) {
		top = Math.min(top, minY)
	}
	if (bottom > maxY - CROP_MARGIN) {
		bottom = Math.max(bottom, maxY)
	}
	if (top < minY) {
		bottom = Math.min(maxY, bottom + (minY - top))
		top = minY
	}
	if (bottom > maxY) {
		top = Math.max(minY, top - (bottom - maxY))
		bottom = maxY
	}
	return { x: FULL_VIEW.x, y: top, width: FULL_VIEW.width, height: bottom - top }
}

/** The player on the ball, if the picture has one. */
export const carrierOf = (picture: Picture): Marker | undefined => picture.markers.find(m => m.role === 'on the ball')

/** The screen points a moment's view must show: the ball, the carrier, each option and the path. */
export const momentPoints = (picture: Picture, options: readonly PitchOption[], path: readonly Point[]): Point[] => {
	const carrier = carrierOf(picture)
	return [
		picture.ball,
		...(carrier === undefined ? [] : [[carrier.x, carrier.y] as const]),
		...options.map(o => o.at),
		...path
	].map(toScreen)
}

/** Whether a marker takes part in the moment: on the ball, at an option's target, or on the path. */
export const isInvolved = (marker: Marker, options: readonly PitchOption[], path: readonly Point[]): boolean => {
	if (marker.role === 'on the ball') {
		return true
	}
	const near = ([x, y]: Point) => Math.hypot(marker.x - x, marker.y - y) <= INVOLVED_WITHIN
	return options.some(o => near(o.at)) || path.some(near)
}

/** Where to draw the ball: just ahead of its carrier (upwards on screen) so the two don't overlap. */
export const ballOnScreen = (picture: Picture): Point => {
	const [x, y] = toScreen(picture.ball)
	const carrier = carrierOf(picture)
	if (carrier === undefined || Math.hypot(carrier.x - picture.ball[0], carrier.y - picture.ball[1]) > 1) {
		return [x, y]
	}
	return [x + BALL_OFFSET, y - BALL_OFFSET]
}

/** An SVG path through the screen points. */
export const pathData = (points: readonly Point[]) =>
	points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${String(round(x))} ${String(round(y))}`).join(' ')

/**
 * Where an option's letter sits: beside the middle of its line, on whichever side is further from the players, so it
 * covers neither the line nor a player.
 */
export const tagPosition = (from: Point, to: Point, players: readonly Point[] = []): Point => {
	const [x1, y1] = from
	const [x2, y2] = to
	const length = Math.hypot(x2 - x1, y2 - y1) || 1
	const [nx, ny] = [-(y2 - y1) / length, (x2 - x1) / length]
	const [mx, my] = [(x1 + x2) / 2, (y1 + y2) / 2]
	const sides: Point[] = [
		[mx + nx * TAG_OFFSET, my + ny * TAG_OFFSET],
		[mx - nx * TAG_OFFSET, my - ny * TAG_OFFSET]
	]
	const clearance = ([x, y]: Point) => Math.min(Infinity, ...players.map(([px, py]) => Math.hypot(px - x, py - y)))
	const [first, second] = sides as [Point, Point]
	return clearance(second) > clearance(first) ? second : first
}

/** The pitch markings, in screen metres: outline, halfway line, centre circle and spot, both boxes. */
export const MARKINGS = {
	outline: { x: 0, y: 0, width: PITCH_WIDTH, height: PITCH_LENGTH },
	halfway: PITCH_LENGTH / 2,
	centre: { x: PITCH_WIDTH / 2, y: PITCH_LENGTH / 2, r: 9.15 },
	boxes: [boxPair(40.32, 16.5), boxPair(18.32, 5.5)].flat(),
	spots: [
		[PITCH_WIDTH / 2, 11],
		[PITCH_WIDTH / 2, PITCH_LENGTH / 2],
		[PITCH_WIDTH / 2, PITCH_LENGTH - 11]
	] as const
}

function boxPair(width: number, depth: number) {
	const x = (PITCH_WIDTH - width) / 2
	return [
		{ x, y: 0, width, height: depth },
		{ x, y: PITCH_LENGTH - depth, width, height: depth }
	]
}

/**
 * Plain words for where a point is, as the team on the ball sees it: "on the left, in the attacking third".
 *
 * Only splits the given coordinates into thirds; it judges nothing about the play.
 */
export const placeWords = ([x, y]: Point): string => {
	const side = y > (PITCH_WIDTH * 2) / 3 ? 'on the left' : y < PITCH_WIDTH / 3 ? 'on the right' : 'in the centre'
	const third =
		x >= (PITCH_LENGTH * 2) / 3 ? 'attacking third' : x >= PITCH_LENGTH / 3 ? 'middle third' : 'defensive third'
	return `${side}, in the ${third}`
}

/** What a screen reader hears for the pitch: who has the ball, which way they attack, and where each option is. */
export const describePitch = (label: string, picture: Picture, options: readonly PitchOption[]): string => {
	const carrier = carrierOf(picture)
	const sentences = [label, 'The team on the ball is attacking upwards.']
	if (carrier !== undefined) {
		sentences.push(`Number ${String(carrier.shirt)} has the ball, ${placeWords([carrier.x, carrier.y])}.`)
	}
	for (const option of options) {
		sentences.push(`${option.key}: ${placeWords(option.at)}.`)
	}
	return sentences.map(s => s.trim().replace(/\.?$/, '.')).join(' ')
}

const round = (value: number) => Math.round(value * 100) / 100
