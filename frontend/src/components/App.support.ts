import type {
	BeforeMatch,
	Club,
	ConceptMap,
	Feedback,
	MatchSummary,
	NextStep,
	Question,
	Report,
	Status,
	TeamSheet
} from '../api/client.ts'

/** A point in a match: when the last question was asked, so the page knows when the viewer reached the second half. */
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
	| { kind: 'matches' }
	| { kind: 'pick'; status: Status }
	| { kind: 'choose'; club: number }
	| { kind: 'sheet'; status: Status | null }
	| { kind: 'before'; status: Status | null }
	| { kind: 'answer'; question: Question; key: string }

export type BeforeFlow = 'first_look' | 'level_up'

export type Screen =
	| { kind: 'welcome'; error: string | null }
	| { kind: 'matches'; status: Status; matches: MatchSummary[] }
	| { kind: 'pick'; status: Status; clubs: Club[]; busy: boolean }
	| { kind: 'sheet'; sheet: TeamSheet; status: Status | null }
	/** A story flow before a match: First look at new concepts, or Level-ups since the last match; then Who's playing. */
	| { kind: 'before'; before: BeforeMatch; flow: BeforeFlow; status: Status | null }
	| { kind: 'loading'; message: string }
	| { kind: 'step'; question: Question }
	| { kind: 'question'; question: Question; busy: boolean }
	| { kind: 'feedback'; question: Question; feedback: Feedback }
	/** A scouting report; `then` is the question to go on to after halftime, or null to go back to Matches. */
	| { kind: 'report'; report: Report; then: Question | null }
	| { kind: 'error'; message: string; retry: Retry }

/** A sheet over the current screen, which stays as it was underneath: the curriculum map or Preferences, opened from
 * any header. */
export type Overlay =
	| { kind: 'map'; map: ConceptMap | null; error: string | null }
	| { kind: 'preferences'; status: Status | null; busy: boolean }

export interface AppState {
	viewer: string | null
	screen: Screen
	/** When the last question was asked, in the match being watched. */
	last: Moment | null
	overlay: Overlay | null
	/** The matches whose halftime report has been shown, so each shows once. */
	halftimes: number[]
}

export type Action =
	| { type: 'loading'; message: string }
	| { type: 'matches'; status: Status; matches: MatchSummary[] }
	| { type: 'picking'; status: Status; clubs: Club[] }
	| { type: 'choosing' }
	| { type: 'sheet'; sheet: TeamSheet; status: Status | null }
	| { type: 'before'; before: BeforeMatch; flow: BeforeFlow; status: Status | null }
	| { type: 'rejected'; message: string }
	| { type: 'forget'; message?: string }
	| { type: 'arrived'; step: Question }
	| { type: 'report'; report: Report; then: Question | null }
	| { type: 'open' }
	| { type: 'sending' }
	| { type: 'answered'; feedback: Feedback }
	| { type: 'failed'; message: string; retry: Retry }
	| { type: 'map'; map: ConceptMap | null; error?: string }
	| { type: 'preferences'; status: Status | null; busy?: boolean }
	| { type: 'close' }

export const LOADING_NEXT = 'The match moves on…'
export const LOADING_START = 'Finding your place…'
export const LOADING_MATCHES = 'Finding your matches…'
export const LOADING_CLUBS = 'Finding the clubs…'
export const LOADING_SHEET = 'Finding the line-ups…'
export const LOADING_BEFORE = 'Checking your levels…'
export const LOADING_REPORT = 'Writing the report…'

/** A viewer who hasn't picked a team yet, and still can: they are asked before anything else. */
export const needsClub = (status: Status) => status.club === null && status.can_choose_club && !status.finished

export const welcome = (error: string | null = null): Screen => ({ kind: 'welcome', error })

/** The first state: straight to loading when a viewer is remembered, since the page resumes them at once. */
export const initialState = (remembered: string | null): AppState =>
	remembered === null
		? { viewer: null, screen: welcome(), last: null, overlay: null, halftimes: [] }
		: {
				viewer: remembered,
				screen: { kind: 'loading', message: LOADING_START },
				last: null,
				overlay: null,
				halftimes: []
			}

export const reducer = (state: AppState, action: Action): AppState => {
	switch (action.type) {
		case 'loading':
			return { ...state, screen: { kind: 'loading', message: action.message } }
		case 'matches':
			return {
				...state,
				viewer: action.status.viewer_id,
				screen: { kind: 'matches', status: action.status, matches: action.matches },
				last: null
			}
		case 'picking':
			return {
				...state,
				viewer: action.status.viewer_id,
				screen: { kind: 'pick', status: action.status, clubs: action.clubs, busy: false },
				last: null
			}
		case 'sheet':
			return { ...state, screen: { kind: 'sheet', sheet: action.sheet, status: action.status }, last: null }
		case 'before':
			return {
				...state,
				screen: { kind: 'before', before: action.before, flow: action.flow, status: action.status },
				last: null
			}
		case 'choosing':
			return state.screen.kind === 'pick' ? { ...state, screen: { ...state.screen, busy: true } } : state
		case 'rejected':
			return { viewer: null, screen: welcome(action.message), last: null, overlay: null, halftimes: [] }
		case 'forget':
			return { viewer: null, screen: welcome(action.message ?? null), last: null, overlay: null, halftimes: [] }
		case 'arrived':
			return arrived(state, action.step)
		case 'report':
			return {
				...state,
				screen: { kind: 'report', report: action.report, then: action.then },
				last: action.report.at === 'full_time' ? null : state.last,
				halftimes:
					action.report.at === 'halftime' ? [...state.halftimes, action.report.match_number] : state.halftimes
			}
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
		case 'map':
			return { ...state, overlay: { kind: 'map', map: action.map, error: action.error ?? null } }
		case 'preferences':
			return { ...state, overlay: { kind: 'preferences', status: action.status, busy: action.busy ?? false } }
		case 'close':
			return { ...state, overlay: null }
	}
}

/** Whether the header offers the map and Preferences: on every screen after the viewer has started and picked a team. */
export const offersMap = (state: AppState) =>
	state.viewer !== null && state.screen.kind !== 'welcome' && state.screen.kind !== 'pick'

/** Whether the page is the welcome, which fills the window on a wide screen: there is no match yet to stand
 * beside. */
export const fillsWindow = (state: AppState) => state.screen.kind === 'welcome'

const arrived = (state: AppState, step: Question): AppState => ({
	...state,
	screen: { kind: 'step', question: step },
	last: momentOf(step)
})

/** Whether a step needs the halftime report first: it is in the second half, and the viewer hasn't had it yet. */
export const needsHalftime = (state: AppState, step: NextStep): boolean =>
	step.kind === 'question' &&
	step.delivered.period > 1 &&
	!state.halftimes.includes(step.match_number) &&
	!(state.last?.matchNumber === step.match_number && state.last.period > 1)

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
		case 'report':
			return {
				title: `${screen.report.home} ${String(screen.report.home_goals)}–${String(screen.report.away_goals)} ${screen.report.away}`,
				clock: screen.report.at === 'halftime' ? 'Halftime' : 'Full time'
			}
		case 'matches':
		case 'before':
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
		case 'welcome':
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
