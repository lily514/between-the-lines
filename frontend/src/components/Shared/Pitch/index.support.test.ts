import type { Question } from '../../../api/client.ts'
import {
	counterQuestion as counter,
	predictFeedback,
	predictQuestion as predict
} from '../../../test-fixtures/index.ts'
import {
	FULL_VIEW,
	PITCH_LENGTH,
	PITCH_WIDTH,
	ballOnScreen,
	carrierOf,
	cropTo,
	describePitch,
	isInvolved,
	momentPoints,
	placeWords,
	tagPosition,
	toScreen,
	type PitchOption,
	type Point
} from './index.support.ts'

const optionsOf = (question: Question): PitchOption[] =>
	question.options.flatMap(o => (o.target_at === null ? [] : [{ key: o.key, at: o.target_at }]))

const inside = ([x, y]: Point, view: typeof FULL_VIEW) =>
	x >= view.x && x <= view.x + view.width && y >= view.y && y <= view.y + view.height

test('the attacker’s left is on the left of the screen and their goal is at the top', () => {
	const [leftX] = toScreen([50, PITCH_WIDTH])
	const [rightX] = toScreen([50, 0])
	expect(leftX).toBe(0)
	expect(rightX).toBe(PITCH_WIDTH)
	const [, nearGoalY] = toScreen([PITCH_LENGTH, 34])
	const [, ownGoalY] = toScreen([0, 34])
	expect(nearGoalY).toBe(0)
	expect(ownGoalY).toBe(PITCH_LENGTH)
})

test('a moment’s view keeps the full width and shows the ball and every option', () => {
	const options = optionsOf(predict)
	const view = cropTo(momentPoints(predict.picture, options, []))
	expect(view.x).toBe(FULL_VIEW.x)
	expect(view.width).toBe(FULL_VIEW.width)
	expect(view.height).toBeLessThan(FULL_VIEW.height)
	for (const point of momentPoints(predict.picture, options, [])) {
		expect(inside(point, view)).toBe(true)
	}
})

test('the reveal’s view also shows the whole real path', () => {
	const path = predictFeedback.reveal_path
	const view = cropTo(momentPoints(predictFeedback.picture, [], path))
	for (const point of path.map(toScreen)) {
		expect(inside(point, view)).toBe(true)
	}
})

test('a view never reaches beyond the pitch’s border', () => {
	for (const points of [[[34, -20] as const], [[34, 130] as const], [[34, 0] as const, [34, 105] as const]]) {
		const view = cropTo(points)
		expect(view.y).toBeGreaterThanOrEqual(FULL_VIEW.y)
		expect(view.y + view.height).toBeLessThanOrEqual(FULL_VIEW.y + FULL_VIEW.height)
	}
})

test('a short moment still gets a view of at least fifty metres', () => {
	const view = cropTo([[34, 50]])
	expect(view.height).toBe(50)
	expect(view.y).toBe(25)
})

test('a play from one end to the other shows both goal lines', () => {
	const endToEnd: Point[] = [
		[8, 30],
		[60, 40],
		[100, 34]
	]
	const view = cropTo(momentPoints(counter.picture, [], endToEnd))
	expect(view.y).toBeLessThanOrEqual(0)
	expect(view.y + view.height).toBeGreaterThanOrEqual(PITCH_LENGTH - 15)
})

test('the player on the ball and the players at the options take part, others do not', () => {
	const options = optionsOf(predict)
	const involved = predict.picture.markers.filter(m => isInvolved(m, options, []))
	expect(involved.some(m => m.role === 'on the ball')).toBe(true)
	expect(involved.length).toBe(1 + options.length)
})

test('place words split the coordinates into thirds', () => {
	expect(placeWords([90, 60])).toBe('on the left, in the attacking third')
	expect(placeWords([50, 34])).toBe('in the centre, in the middle third')
	expect(placeWords([10, 5])).toBe('on the right, in the defensive third')
})

test('a screen reader hears who has the ball and where each option is', () => {
	const text = describePitch('Freeze-frame at 05:12', predict.picture, optionsOf(predict))
	expect(text).toContain('Freeze-frame at 05:12.')
	expect(text).toContain('attacking upwards')
	expect(text).toMatch(/Number \d+ has the ball/)
	for (const option of predict.options) {
		expect(text).toContain(`${option.key}: `)
	}
})

test('an option’s letter sits beside its line, not on it', () => {
	const [x, y] = tagPosition([0, 0], [0, 10])
	expect(y).toBe(5)
	expect(Math.abs(x)).toBeGreaterThan(2)
})

test('an option\u2019s letter goes on the side of its line away from a player', () => {
	const [x] = tagPosition([0, 0], [0, 10], [[-2.6, 5]])
	expect(x).toBeGreaterThan(0)
	const [otherX] = tagPosition([0, 0], [0, 10], [[2.6, 5]])
	expect(otherX).toBeLessThan(0)
})

test('a view that comes close to a goal line shows the goal line', () => {
	const view = cropTo([[34, 5]])
	expect(view.y).toBe(FULL_VIEW.y)
})

test('the ball sits beside the player on it, clear of the shirt number', () => {
	const carrier = carrierOf(predict.picture)
	if (carrier === undefined) throw new Error('the fixture has a player on the ball')
	const [cx, cy] = toScreen([carrier.x, carrier.y])
	const [bx, by] = ballOnScreen(predict.picture)
	// The disc has radius 2.2; with its centre outside it, the ball only touches the disc's edge.
	expect(Math.hypot(bx - cx, by - cy)).toBeGreaterThan(2.2)
})
