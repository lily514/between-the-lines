import { sheetStage1, sheetStage2, sheetStage3 } from '../../test-fixtures/index.ts'
import { groupsOf, kickoffPicture, watchedLine, yourSide } from './index.support.ts'

test('starters are grouped goalkeeper to forwards, keeping each line in order', () => {
	const team = sheetStage1.teams[0]
	if (team === undefined) throw new Error('no team')
	const groups = groupsOf(team)
	expect(groups.map(group => [group.heading, group.players.length])).toEqual([
		['Goalkeeper', 1],
		['Defenders', 4],
		['Midfielders', 4],
		['Forwards', 2]
	])
	expect(groups[1]?.players.map(p => p.position.short)).toEqual(['LB', 'CB', 'CB', 'RB'])
})

test('the viewer’s side comes from the team marked as theirs', () => {
	expect(yourSide(sheetStage1)).toBe('home')
	expect(yourSide(sheetStage3)).toBe('away')
	expect(yourSide({ ...sheetStage1, teams: sheetStage1.teams.map(t => ({ ...t, yours: false })) })).toBeNull()
})

test('the kick-off picture has all 22 starters from stage 2, and none before', () => {
	expect(kickoffPicture(sheetStage1)).toBeNull()
	const picture = kickoffPicture(sheetStage2)
	expect(picture?.markers).toHaveLength(22)
	expect(picture?.markers.filter(m => m.side === 'attacking').every(m => !m.home)).toBe(true)
})

test('a club’s line says how many of its matches the numbers come from', () => {
	const [yours, theirs] = sheetStage3.teams
	if (yours === undefined || theirs === undefined) throw new Error('no teams')
	expect(watchedLine(yours)).toBe("From the 2 matches of theirs you've watched.")
	expect(watchedLine(theirs)).toBe("You haven't watched Bakewell Badgers yet, so there are no numbers for them.")
	expect(watchedLine({ ...yours, matches_watched: 1 })).toBe("From the 1 match of theirs you've watched.")
	expect(watchedLine({ ...yours, matches_watched: null })).toBeNull()
})
