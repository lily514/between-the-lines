import type { Picture, SheetPlayer, SheetTeam, TeamSheet } from '../../api/client.ts'

/** The position groups, in the order a team sheet lists them. */
export const GROUPS: readonly { role: string; heading: string }[] = [
	{ role: 'GK', heading: 'Goalkeeper' },
	{ role: 'DF', heading: 'Defenders' },
	{ role: 'MF', heading: 'Midfielders' },
	{ role: 'FW', heading: 'Forwards' }
]

/** A team's starters by position group, keeping the API's order (each line left to right). */
export const groupsOf = (team: SheetTeam): { heading: string; players: SheetPlayer[] }[] =>
	GROUPS.map(group => ({ heading: group.heading, players: team.players.filter(p => p.role === group.role) })).filter(
		group => group.players.length > 0
	)

/** Which side is the viewer's team, if either. */
export const yourSide = (sheet: TeamSheet): 'home' | 'away' | null => {
	const yours = sheet.teams.find(team => team.yours)
	return yours === undefined ? null : yours.home ? 'home' : 'away'
}

/** Both elevens at kick-off as a pitch picture, the sheet's first team attacking up; null before stage 2. The picture
 * has no ball, so its ball is never drawn. */
export const kickoffPicture = (sheet: TeamSheet): Picture | null => {
	const markers = sheet.teams.flatMap((team, index) =>
		team.players.flatMap(player =>
			player.at_kickoff === null
				? []
				: [
						{
							shirt: player.shirt,
							side: index === 0 ? ('attacking' as const) : ('defending' as const),
							home: team.home,
							x: player.at_kickoff[0],
							y: player.at_kickoff[1],
							role: player.position.name
						}
					]
		)
	)
	if (markers.length === 0) {
		return null
	}
	const first = markers[0]
	return {
		action_id: 0,
		markers,
		ball: first === undefined ? [0, 0] : [first.x, first.y],
		path: [],
		mark: null
	}
}

/** The line under a team's card at stage 3: how many of its matches the numbers come from. */
export const watchedLine = (team: SheetTeam): string | null => {
	if (team.matches_watched === null) {
		return null
	}
	if (team.matches_watched === 0) {
		return `You haven't watched ${team.name} yet, so there are no numbers for them.`
	}
	const matches = team.matches_watched === 1 ? 'match' : 'matches'
	return `From the ${String(team.matches_watched)} ${matches} of theirs you've watched.`
}
