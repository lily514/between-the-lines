// Hand-built payloads for tests where no captured one exists: a viewer's status and a full-time summary. Their shapes
// are checked against the generated API types.
import type { FullTime, Status } from '../api/client.ts'

export const startStatus: Status = {
	viewer_id: 'lily',
	match_number: 1,
	matches: 3,
	finished: false,
	fixture: { home: 'Ripon Wardens', away: 'Ludlow Ferrymen' },
	concepts: [
		{ name: 'Line-breaking passes', value: 0.15 },
		{ name: 'Counter-pressing', value: 0.17 }
	],
	thresholds: { unlock: 0.8, mastery: 0.95 }
}

export const finishedStatus: Status = { ...startStatus, match_number: 3, finished: true, fixture: null }

export const fullTime: FullTime = {
	kind: 'full_time',
	match_number: 1,
	home: 'Ripon Wardens',
	away: 'Ludlow Ferrymen',
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
