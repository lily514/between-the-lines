import {
	beforeMatchLevelUp,
	conceptMap,
	identifyFeedback,
	identifyQuestion,
	matchesInProgress,
	predictQuestion,
	reportFullTime,
	reportHalftime
} from '../test-fixtures/index.ts'
import { startStatus } from '../test-fixtures/summaries.ts'
import {
	initialState,
	matchHeader,
	momentOf,
	needsHalftime,
	newViewerId,
	offersMap,
	reducer,
	type AppState
} from './App.support.ts'

const fresh = initialState(null)
const watching = (
	state: AppState = reducer(fresh, { type: 'matches', status: startStatus, matches: matchesInProgress })
) => state

test('a new visitor starts at the welcome', () => {
	expect(fresh.viewer).toBeNull()
	expect(fresh.screen).toEqual({ kind: 'welcome', error: null })
	expect(fresh.overlay).toBeNull()
})

// The API's viewer id rule (`check_viewer_id` in backend/src/btl/store/base.py).
const VIEWER_ID_RULE = /^[a-z0-9][a-z0-9_-]{0,63}$/

test('a new viewer id is one the API accepts, and never the same twice', () => {
	const ids = Array.from({ length: 100 }, newViewerId)
	for (const id of ids) {
		expect(id).toMatch(VIEWER_ID_RULE)
		expect(id).toMatch(/^[0-9a-f]{32}$/)
	}
	expect(new Set(ids).size).toBe(ids.length)
})

test('a remembered viewer starts by loading, since the page resumes them at once', () => {
	const state = initialState('lily')
	expect(state.viewer).toBe('lily')
	expect(state.screen.kind).toBe('loading')
})

test('starting lands on Matches, home base', () => {
	const state = watching()
	expect(state.viewer).toBe('lily')
	expect(state.screen).toEqual({ kind: 'matches', status: startStatus, matches: matchesInProgress })
})

test('a refused id returns to the welcome with the reason', () => {
	const state = reducer(fresh, { type: 'rejected', message: 'not a valid viewer id' })
	expect(state.viewer).toBeNull()
	expect(state.screen).toEqual({ kind: 'welcome', error: 'not a valid viewer id' })
})

test('a question arrives as a step, then opens as the question sheet', () => {
	const step = reducer(watching(), { type: 'arrived', step: identifyQuestion })
	expect(step.screen).toEqual({ kind: 'step', question: identifyQuestion })
	expect(step.last).toEqual(momentOf(identifyQuestion))
	const open = reducer(step, { type: 'open' })
	expect(open.screen).toEqual({ kind: 'question', question: identifyQuestion, busy: false })
})

test('sending marks the sheet busy, and the answer shows the feedback for that question', () => {
	const open = reducer(reducer(watching(), { type: 'arrived', step: identifyQuestion }), { type: 'open' })
	const sending = reducer(open, { type: 'sending' })
	expect(sending.screen).toMatchObject({ kind: 'question', busy: true })
	const told = reducer(sending, { type: 'answered', feedback: identifyFeedback })
	expect(told.screen).toEqual({ kind: 'feedback', question: identifyQuestion, feedback: identifyFeedback })
})

test('an answer that arrives when no question is open is ignored', () => {
	const state = watching()
	expect(reducer(state, { type: 'answered', feedback: identifyFeedback })).toBe(state)
	expect(reducer(state, { type: 'open' })).toBe(state)
})

test('the full-time report forgets where the last question was, and goes back to Matches after', () => {
	const first = reducer(watching(), { type: 'arrived', step: identifyQuestion })
	const end = reducer(first, { type: 'report', report: reportFullTime, then: null })
	expect(end.screen).toEqual({ kind: 'report', report: reportFullTime, then: null })
	expect(end.last).toBeNull()
})

test('the halftime report shows once per match, before the first second-half question', () => {
	const second = { ...predictQuestion, match_number: 1, delivered: { ...predictQuestion.delivered, period: 2 } }
	const first = reducer(watching(), { type: 'arrived', step: { ...identifyQuestion, match_number: 1 } })
	expect(needsHalftime(first, second)).toBe(true)
	expect(needsHalftime(first, { ...identifyQuestion, match_number: 1 })).toBe(false)
	const shown = reducer(first, { type: 'report', report: reportHalftime, then: second })
	expect(shown.screen).toMatchObject({ kind: 'report', then: second })
	expect(shown.halftimes).toEqual([1])
	expect(needsHalftime(shown, second)).toBe(false)
	expect(needsHalftime(reducer(first, { type: 'arrived', step: second }), second)).toBe(false)
})

test('a failure keeps what to retry', () => {
	const open = reducer(reducer(watching(), { type: 'arrived', step: identifyQuestion }), { type: 'open' })
	const retry = { kind: 'answer', question: identifyQuestion, key: 'A' } as const
	const failed = reducer(open, { type: 'failed', message: 'offline', retry })
	expect(failed.screen).toEqual({ kind: 'error', message: 'offline', retry })
	expect(failed.viewer).toBe('lily')
})

test('forgetting the viewer goes back to the welcome', () => {
	const state = reducer(watching(), { type: 'forget', message: 'That record has gone.' })
	expect(state.viewer).toBeNull()
	expect(state.screen).toEqual({ kind: 'welcome', error: 'That record has gone.' })
})

test('the wide-screen header names the match being watched', () => {
	expect(matchHeader({ kind: 'step', question: identifyQuestion })).toEqual({
		title: 'Ripon Wardens v Ludlow Ferrymen',
		clock: '13:59'
	})
	expect(matchHeader({ kind: 'report', report: reportFullTime, then: null })).toEqual({
		title: 'Ripon Wardens 1–0 Truro Otters',
		clock: 'Full time'
	})
	expect(matchHeader({ kind: 'loading', message: '…' })).toBeNull()
	const before = {
		kind: 'before' as const,
		before: beforeMatchLevelUp,
		flow: 'level_up' as const,
		status: startStatus
	}
	expect(matchHeader(before)).toEqual({ title: 'Ripon Wardens v Ludlow Ferrymen', clock: null })
	expect(matchHeader({ ...before, status: null })).toBeNull()
})

test('a flow before the match is a screen of its own, with the map on offer', () => {
	const state = reducer(watching(), {
		type: 'before',
		before: beforeMatchLevelUp,
		flow: 'first_look',
		status: startStatus
	})
	expect(state.screen).toEqual({
		kind: 'before',
		before: beforeMatchLevelUp,
		flow: 'first_look',
		status: startStatus
	})
	expect(state.last).toBeNull()
	expect(offersMap(state)).toBe(true)
})

test('the map opens over the screen and closing it leaves the screen as it was', () => {
	const open = reducer(reducer(watching(), { type: 'arrived', step: identifyQuestion }), { type: 'open' })
	const loading = reducer(open, { type: 'map', map: null })
	expect(loading.overlay).toEqual({ kind: 'map', map: null, error: null })
	const loaded = reducer(loading, { type: 'map', map: conceptMap })
	expect(loaded.screen).toBe(open.screen)
	const closed = reducer(loaded, { type: 'close' })
	expect(closed.overlay).toBeNull()
	expect(closed.screen).toBe(open.screen)
})

test('the header offers the map once the viewer has picked a team, not during onboarding', () => {
	expect(offersMap(fresh)).toBe(false)
	expect(offersMap(reducer(fresh, { type: 'picking', status: startStatus, clubs: [] }))).toBe(false)
	expect(offersMap(watching())).toBe(true)
	expect(offersMap(reducer(watching(), { type: 'arrived', step: identifyQuestion }))).toBe(true)
})
