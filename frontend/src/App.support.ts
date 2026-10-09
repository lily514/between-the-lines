import type { Feedback, FullTime, NextStep, Question, Status } from './api/client.ts'

/** A point in a match: where the last question left the viewer, so the next step can say how far play moved on. */
export interface Moment {
	matchNumber: number
	clock: string
	period: number
	seconds: number
}

/** What a failed request should do when the viewer asks to try again. */
export type Retry =
	| { kind: 'start'; name: string }
	| { kind: 'next' }
	| { kind: 'status' }
	| { kind: 'answer'; question: Question; key: string }

export type Screen =
	| { kind: 'welcome'; status: Status | null; error: string | null; name: string }
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
	| { type: 'rejected'; message: string; name: string }
	| { type: 'forget'; message?: string }
	| { type: 'arrived'; step: NextStep }
	| { type: 'open' }
	| { type: 'sending' }
	| { type: 'answered'; feedback: Feedback }
	| { type: 'failed'; message: string; retry: Retry }

export const LOADING_NEXT = 'The match moves on…'
export const LOADING_START = 'Finding your matches…'

export const welcome = (error: string | null = null, name = ''): Screen => ({
	kind: 'welcome',
	status: null,
	error,
	name
})

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
				screen: { kind: 'welcome', status: action.status, error: null, name: action.status.viewer_id },
				last: null
			}
		case 'rejected':
			return { viewer: null, screen: welcome(action.message, action.name), last: null }
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
		case 'loading':
		case 'error':
			return null
	}
}

const VIEWER_KEY = 'btl.viewer'

// Remembering the name is a convenience for this browser only; storage can be missing or blocked, so every access is
// guarded and the page works without it.
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
		// Not remembered: the viewer types their name again next time.
	}
}

export const forgetViewer = () => {
	try {
		localStorage.removeItem(VIEWER_KEY)
	} catch {
		// Nothing to forget.
	}
}
