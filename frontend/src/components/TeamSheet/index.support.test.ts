import { sheetStage1, sheetStage3 } from '../../test-fixtures/index.ts'
import {
	firstPick,
	labelBox,
	pitchLabel,
	shirtName,
	spotsOf,
	spreadOut,
	teamWords,
	watchedLine,
	yourSide
} from './index.support.ts'

test('every starter has a spot, the first team’s keeper at the bottom attacking up', () => {
	const spots = spotsOf(sheetStage1)
	expect(spots).toHaveLength(22)
	expect(new Set(spots.map(s => s.key)).size).toBe(22)
	const [keeper] = spots
	expect(keeper?.player.role).toBe('GK')
	expect(keeper?.at[1]).toBeGreaterThan(90)
	expect(spots.filter(s => s.team === sheetStage1.teams[1]).every(s => s.at[1] < 105)).toBe(true)
})

test('overlapping players are nudged apart just enough to tap, and the rest stay where the API put them', () => {
	const [a, b, c] = spreadOut([
		[30, 40],
		[31, 40],
		[60, 90]
	])
	if (a === undefined || b === undefined || c === undefined) throw new Error('points lost')
	expect(Math.hypot(b[0] - a[0], b[1] - a[1])).toBeCloseTo(5.2)
	expect((a[0] + b[0]) / 2).toBeCloseTo(30.5)
	expect(c).toEqual([60, 90])
	const [left, right] = spreadOut([
		[0, 10],
		[0, 10]
	])
	expect(left?.[0]).toBeGreaterThanOrEqual(0)
	expect(right?.[0]).toBeGreaterThan(left?.[0] ?? 0)
	for (const sheet of [sheetStage1, sheetStage3]) {
		const at = spotsOf(sheet).map(s => s.at)
		const closest = Math.min(
			...at.flatMap((p, i) => at.slice(i + 1).map(q => Math.hypot(p[0] - q[0], p[1] - q[1])))
		)
		expect(closest).toBeGreaterThan(5)
	}
})

test('the card first shows the first team’s first forward', () => {
	const pick = firstPick(spotsOf(sheetStage1))
	expect([pick?.team.code, pick?.player.role, pick?.player.shirt]).toEqual(['RIP', 'FW', 9])
	expect(firstPick([])).toBeUndefined()
})

test('the pitch label adds the position tag from stage two, and stays on the pitch', () => {
	const pick = firstPick(spotsOf(sheetStage1))
	if (pick === undefined) throw new Error('no players')
	expect(pitchLabel(pick, false)).toBe('#9 Adama Trafo')
	expect(pitchLabel(pick, true)).toBe('#9 Adama Trafo · ST')
	const nearCorner = labelBox([1, 2], 'A long label for a player')
	expect(nearCorner.x).toBeGreaterThanOrEqual(0)
	expect(nearCorner.y).toBeGreaterThan(2)
	const farRight = labelBox([67, 50], 'A long label for a player')
	expect(farRight.x + farRight.width).toBeLessThanOrEqual(68)
	expect(farRight.y + farRight.height).toBeLessThan(50)
})

test('a player’s shirt name is their surname from the server, all of it', () => {
	const player = sheetStage1.teams[0]?.players[1]
	if (player === undefined) throw new Error('no player')
	expect(shirtName(player)).toBe('Hafkamp')
	expect(shirtName({ ...player, name: 'Joost de Witkamp', surname: 'de Witkamp' })).toBe('de Witkamp')
})

test('the viewer’s side comes from the team marked as theirs', () => {
	expect(yourSide(sheetStage1)).toBe('home')
	expect(yourSide(sheetStage3)).toBe('away')
	expect(yourSide({ ...sheetStage1, teams: sheetStage1.teams.map(t => ({ ...t, yours: false })) })).toBeNull()
})

test('the card names the player’s club, home or away, and whether it is the viewer’s', () => {
	const [yours, theirs] = sheetStage3.teams
	if (yours === undefined || theirs === undefined) throw new Error('no teams')
	expect(teamWords(yours)).toBe('Hexham Anchors · away · your team')
	expect(teamWords(theirs)).toBe('Bakewell Badgers · home')
})

test('a club’s line says how many of its matches the numbers come from', () => {
	const [yours, theirs] = sheetStage3.teams
	if (yours === undefined || theirs === undefined) throw new Error('no teams')
	expect(watchedLine(yours)).toBe("From the 2 matches of theirs you've watched.")
	expect(watchedLine(theirs)).toBe("You haven't watched Bakewell Badgers yet, so there are no numbers for them.")
	expect(watchedLine({ ...yours, matches_watched: 1 })).toBe("From the 1 match of theirs you've watched.")
	expect(watchedLine({ ...yours, matches_watched: null })).toBeNull()
})
