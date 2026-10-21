// Hand-built payloads for tests where no captured one exists: a viewer's status and a full-time summary. Their shapes
// are checked against the generated API types.
import type { Club, FullTime, Status } from '../api/client.ts'

export const clubs: Club[] = [
	{ team_id: 1, name: 'Ripon Wardens', code: 'RIP' },
	{ team_id: 2, name: 'Hexham Anchors', code: 'HEX' },
	{ team_id: 3, name: 'Alnwick Weavers', code: 'ALN' }
]

/** A viewer who has picked their team and not yet answered anything. */
export const startStatus: Status = {
	viewer_id: 'lily',
	match_number: 1,
	matches: 3,
	finished: false,
	fixture: { home: 'Ripon Wardens', away: 'Ludlow Ferrymen', home_code: 'RIP', away_code: 'LUD', your_team: 'home' },
	club: { team_id: 1, name: 'Ripon Wardens', code: 'RIP' },
	can_choose_club: true,
	suggested_club: 2,
	concepts: [
		{ name: 'Line-breaking passes', value: 0.15 },
		{ name: 'Counter-pressing', value: 0.17 }
	],
	thresholds: { unlock: 0.8, mastery: 0.95 }
}

/** A new viewer, before picking a team. */
export const newStatus: Status = {
	...startStatus,
	club: null,
	fixture: { home: 'Wells Comets', away: 'Truro Otters', home_code: 'WEL', away_code: 'TRU', your_team: null }
}

export const finishedStatus: Status = {
	...startStatus,
	match_number: 3,
	finished: true,
	fixture: null,
	can_choose_club: false
}

export const fullTime: FullTime = {
	kind: 'full_time',
	match_number: 1,
	home: 'Ripon Wardens',
	away: 'Ludlow Ferrymen',
	home_code: 'RIP',
	away_code: 'LUD',
	your_team: null,
	home_goals: 2,
	away_goals: 1,
	questions: 1,
	concepts: [
		{ name: 'Line-breaking passes', before: 0.15, after: 0.42 },
		{ name: 'Counter-pressing', before: 0.17, after: 0.17 }
	],
	thresholds: { unlock: 0.8, mastery: 0.95 },
	finished: false,
	next_match: 2
}

export const lastFullTime: FullTime = { ...fullTime, match_number: 3, finished: true, next_match: null }
