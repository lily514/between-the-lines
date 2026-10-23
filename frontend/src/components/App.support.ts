import type { Club, Feedback, FullTime, NextStep, Question, Status, TeamSheet } from '../api/client.ts'

/** A point in a match: where the last question left the viewer, so the next step can say how far play moved on. */
export interface Moment {
	matchNumber: number
	clock: string
	period: number
	seconds: number
}

/** What a failed request should do when the viewer asks to try again. */
export type Retry =
	| { kind: 'start'; viewer: string }
	| { kind: 'next' }
	| { kind: 'status' }
	| { kind: 'pick'; status: Status }
	| { kind: 'choose'; club: number }
	| { kind: 'sheet'; status: Status | null }
	| { kind: 'answer'; question: Question; key: string }

export type Screen =
	| { kind: 'welcome'; status: Status | null; error: string | null }
	| { kind: 'pick'; status: Status; clubs: Club[]; busy: boolean }
	| { kind: 'sheet'; sheet: TeamSheet; status: Status | null }
	| { kind: 'loading'; message: string }
	| { kind: 'step'; question: Question; from: Moment | null }
	| { kind: 'question'; question: Question; busy: boolean }
	| { kind: 'feedback'; question: Question; feedback: Feedback }
	| { kind: 'full_time'; summary: FullTime }
	| { kind: 'error'; message: string; retry: Retry }

export interface AppState {
	viewer: string | null
	screen: Screen
	/** When the last question was asked, in the match being watched. */
	last: Moment | null
}

export type Action =
	| { type: 'loading'; message: string }
	| { type: 'started'; status: Status }
	| { type: 'picking'; status: Status; clubs: Club[] }
	| { type: 'choosing' }
	| { type: 'sheet'; sheet: TeamSheet; status: Status | null }
	| { type: 'rejected'; message: string }
	| { type: 'forget'; message?: string }
	| { type: 'arrived'; step: NextStep }
	| { type: 'open' }
	| { type: 'sending' }
	| { type: 'answered'; feedback: Feedback }
	| { type: 'failed'; message: string; retry: Retry }

export const LOADING_NEXT = 'The match moves on…'
export const LOADING_START = 'Finding your matches…'
export const LOADING_CLUBS = 'Finding the clubs…'
export const LOADING_SHEET = 'Finding the line-ups…'

/** A viewer who hasn't picked a team yet, and still can: they are asked before anything else. */
export const needsClub = (status: Status) => status.club === null && status.can_choose_club && !status.finished

export const welcome = (error: string | null = null): Screen => ({ kind: 'welcome', status: null, error })

/** The first state: straight to loading when a viewer is remembered, since the page resumes them at once. */
export const initialState = (remembered: string | null): AppState =>
	remembered === null
		? { viewer: null, screen: welcome(), last: null }
		: { viewer: remembered, screen: { kind: 'loading', message: LOADING_NEXT }, last: null }

export const reducer = (state: AppState, action: Action): AppState => {
	switch (action.type) {
		case 'loading':
			return { ...state, screen: { kind: 'loading', message: action.message } }
		case 'started':
			return {
				viewer: action.status.viewer_id,
				screen: { kind: 'welcome', status: action.status, error: null },
				last: null
			}
		case 'picking':
			return {
				viewer: action.status.viewer_id,
				screen: { kind: 'pick', status: action.status, clubs: action.clubs, busy: false },
				last: null
			}
		case 'sheet':
			return { ...state, screen: { kind: 'sheet', sheet: action.sheet, status: action.status }, last: null }
		case 'choosing':
			return state.screen.kind === 'pick' ? { ...state, screen: { ...state.screen, busy: true } } : state
		case 'rejected':
			return { viewer: null, screen: welcome(action.message), last: null }
		case 'forget':
			return { viewer: null, screen: welcome(action.message ?? null), last: null }
		case 'arrived':
			return arrived(state, action.step)
		case 'open':
			return state.screen.kind === 'step'
				? { ...state, screen: { kind: 'question', question: state.screen.question, busy: false } }
				: state
		case 'sending':
			return state.screen.kind === 'question' ? { ...state, screen: { ...state.screen, busy: true } } : state
		case 'answered':
			return state.screen.kind === 'question'
				? {
						...state,
						screen: { kind: 'feedback', question: state.screen.question, feedback: action.feedback }
					}
				: state
		case 'failed':
			return { ...state, screen: { kind: 'error', message: action.message, retry: action.retry } }
	}
}

const arrived = (state: AppState, step: NextStep): AppState => {
	if (step.kind === 'full_time') {
		return { ...state, screen: { kind: 'full_time', summary: step }, last: null }
	}
	const from = state.last?.matchNumber === step.match_number ? state.last : null
	return { ...state, screen: { kind: 'step', question: step, from }, last: momentOf(step) }
}

export const momentOf = (question: Question): Moment => ({
	matchNumber: question.match_number,
	clock: question.delivered.clock,
	period: question.delivered.period,
	seconds: question.delivered.seconds
})

/** The match shown above the stream on a wide screen: the clubs, and the clock when a question has one. */
export const matchHeader = (screen: Screen): { title: string; clock: string | null } | null => {
	switch (screen.kind) {
		case 'step':
		case 'question':
		case 'feedback':
			return {
				title: `${screen.question.home} v ${screen.question.away}`,
				clock: screen.question.delivered.clock
			}
		case 'full_time':
			return {
				title: `${screen.summary.home} ${String(screen.summary.home_goals)}–${String(screen.summary.away_goals)} ${screen.summary.away}`,
				clock: 'Full time'
			}
		case 'welcome':
			return screen.status?.fixture
				? { title: `${screen.status.fixture.home} v ${screen.status.fixture.away}`, clock: null }
				: null
		case 'sheet': {
			const home = screen.sheet.teams.find(team => team.home)
			const away = screen.sheet.teams.find(team => !team.home)
			return home !== undefined && away !== undefined
				? { title: `${home.name} v ${away.name}`, clock: null }
				: null
		}
		case 'pick':
		case 'loading':
		case 'error':
			return null
	}
}

const VIEWER_KEY = 'btl.viewer'

/** A new viewer's id: 128 random bits as lower-case hex, which the API's viewer id rule accepts.
 *
 * Nobody can guess it, so it stands in for a sign-in. `getRandomValues` works on any page; `randomUUID` would need
 * HTTPS or localhost. */
export const newViewerId = () =>
	Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('')

// The id is kept in this browser only: it is how a viewer keeps their place between visits. Storage can be missing or
// blocked, so every access is guarded; without it the page still works, and a reload starts a new viewer.
export const rememberedViewer = (): string | null => {
	try {
		return localStorage.getItem(VIEWER_KEY)
	} catch {
		return null
	}
}

export const rememberViewer = (viewer: string) => {
	try {
		localStorage.setItem(VIEWER_KEY, viewer)
	} catch {
		// Not remembered: the next visit starts a new viewer.
	}
}

export const forgetViewer = () => {
	try {
		localStorage.removeItem(VIEWER_KEY)
	} catch {
		// Nothing to forget.
	}
}
