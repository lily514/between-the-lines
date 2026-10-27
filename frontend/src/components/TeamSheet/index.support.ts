import type { SheetPlayer, SheetTeam, TeamSheet } from '../../api/client.ts'
import { PITCH_LENGTH, PITCH_WIDTH, toScreen, type Point } from '../Shared/Pitch/index.support.ts'

/** A starter on the kick-off pitch: who they are, their team and where to draw them, in screen metres. */
export interface Spot {
	key: string
	player: SheetPlayer
	team: SheetTeam
	at: Point
}

/** Which side is the viewer's team, if either. */
export const yourSide = (sheet: TeamSheet): 'home' | 'away' | null => {
	const yours = sheet.teams.find(team => team.yours)
	return yours === undefined ? null : yours.home ? 'home' : 'away'
}

/** Identifies a starter across both teams: shirt numbers repeat between sides. */
export const spotKey = (team: SheetTeam, player: SheetPlayer) => `${team.code}-${String(player.shirt)}`

/** Every starter at kick-off, the sheet's first team attacking up the screen, spread so no two discs overlap. */
export const spotsOf = (sheet: TeamSheet): Spot[] => {
	const starters = sheet.teams.flatMap(team => team.players.map(player => ({ team, player })))
	const spread = spreadOut(starters.map(({ player }) => toScreen(player.at_kickoff)))
	return starters.map(({ team, player }, i) => ({
		key: spotKey(team, player),
		player,
		team,
		at: spread[i] ?? toScreen(player.at_kickoff)
	}))
}

// Discs are 2.4 m across a radius; this leaves a sliver of grass between two, so each can be tapped.
const MIN_APART = 5.2
const SPREAD_ROUNDS = 12

/** Nudges points apart until none are closer than `MIN_APART`, keeping them on the pitch. Moves only what overlaps,
 * and only as far as it must, so the shape stays the one the API sent. */
export const spreadOut = (points: readonly Point[]): Point[] => {
	const at = points.map(([x, y]): [number, number] => [x, y])
	for (let round = 0; round < SPREAD_ROUNDS; round++) {
		let moved = false
		for (let i = 0; i < at.length; i++) {
			for (let j = i + 1; j < at.length; j++) {
				const a = at[i]
				const b = at[j]
				if (a === undefined || b === undefined) continue
				const [dx, dy] = [b[0] - a[0], b[1] - a[1]]
				const apart = Math.hypot(dx, dy)
				if (apart >= MIN_APART) continue
				// Points on top of each other part sideways.
				const [ux, uy] = apart === 0 ? [1, 0] : [dx / apart, dy / apart]
				const push = (MIN_APART - apart) / 2
				a[0] -= ux * push
				a[1] -= uy * push
				b[0] += ux * push
				b[1] += uy * push
				moved = true
			}
		}
		for (const p of at) {
			p[0] = Math.min(Math.max(p[0], 0), PITCH_WIDTH)
			p[1] = Math.min(Math.max(p[1], 0), PITCH_LENGTH)
		}
		if (!moved) break
	}
	return at
}

/** The player the card shows first: the first team's first forward, so the card is never empty. */
export const firstPick = (spots: readonly Spot[]): Spot | undefined => {
	const first = spots[0]?.team
	return spots.find(s => s.team === first && s.player.role === 'FW') ?? spots[0]
}

/** The name in the list and on the pitch label: their last name, as on the back of a shirt. */
export const shirtName = (player: SheetPlayer): string => player.surname

/** What a screen reader hears for a starter, on the pitch and in the list. */
export const spotLabel = ({ player, team }: Spot) =>
	`Number ${String(player.shirt)}, ${player.name}, ${team.name}, ${player.position.name}`

/** What a screen reader hears for the pitch: which side is which, and that the players can be chosen. */
export const describeKickoff = (sheet: TeamSheet) => {
	const [up, down] = sheet.teams
	const side = (team: SheetTeam) =>
		`${team.name}${team.yours ? ', your team' : ''}, ${team.home ? 'filled discs' : 'rings'}`
	return [
		'Kick-off positions.',
		up === undefined ? '' : `${side(up)}, attacking up from the bottom.`,
		down === undefined ? '' : `${side(down)}, at the top.`,
		'Each player is a button: choose one to see who they are.'
	]
		.filter(Boolean)
		.join(' ')
}

/** The name over each half: the club, and its formation from stage 2. */
export const halfLabel = (team: SheetTeam) =>
	`${team.name.toUpperCase()}${team.formation === null ? '' : ` · ${team.formation}`}`

/** The label above the chosen player on the pitch: "#16 Sol Amadi", with the position tag from stage 2. */
export const pitchLabel = ({ player }: Spot, abbreviated: boolean) =>
	`#${String(player.shirt)} ${player.name}${abbreviated ? ` · ${player.position.short}` : ''}`

const LABEL_HEIGHT = 5
// The label's text is 2.7 m tall; a character is about half that wide.
const LABEL_CHARACTER = 1.45
const LABEL_PADDING = 3
const LABEL_GAP = 4.5

/** Where the pitch label sits: above the player, kept on the pitch, or below them if they're at the top. */
export const labelBox = ([x, y]: Point, text: string) => {
	const width = text.length * LABEL_CHARACTER + LABEL_PADDING
	const left = Math.min(Math.max(x - width / 2, 0.5), PITCH_WIDTH - 0.5 - width)
	const above = y - LABEL_GAP - LABEL_HEIGHT
	return { x: left, y: above < 0 ? y + LABEL_GAP : above, width, height: LABEL_HEIGHT }
}

/** The line under a player's name on the card: "Westmere · away · your team". */
export const teamWords = (team: SheetTeam) =>
	[team.name, team.home ? 'home' : 'away', ...(team.yours ? ['your team'] : [])].join(' · ')

/** The line under a player's numbers at stage 3: how many of their team's matches the numbers come from. */
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
