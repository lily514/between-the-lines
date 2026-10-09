import { identifyFeedback, identifyQuestion, predictQuestion } from '../test-fixtures/index.ts'
import { fullTime, startStatus } from '../test-fixtures/summaries.ts'
import { initialState, matchHeader, momentOf, reducer, type AppState } from './App.support.ts'

const fresh = initialState(null)
const watching = (state: AppState = reducer(fresh, { type: 'started', status: startStatus })) => state

test('a new visitor starts at the name form', () => {
	expect(fresh.viewer).toBeNull()
	expect(fresh.screen).toEqual({ kind: 'welcome', status: null, error: null, name: '' })
})

test('a remembered viewer starts by loading, since the page resumes them at once', () => {
	const state = initialState('lily')
	expect(state.viewer).toBe('lily')
	expect(state.screen.kind).toBe('loading')
})

test('starting shows the viewer where they stand', () => {
	const state = watching()
	expect(state.viewer).toBe('lily')
	expect(state.screen).toMatchObject({ kind: 'welcome', status: startStatus })
})

test('a refused name returns to the form with the reason and the name tried', () => {
	const state = reducer(fresh, { type: 'rejected', message: 'not a valid name', name: 'Lily!' })
	expect(state.screen).toEqual({ kind: 'welcome', status: null, error: 'not a valid name', name: 'Lily!' })
})

test('a question arrives as a step from kick-off, then opens as the question sheet', () => {
	const step = reducer(watching(), { type: 'arrived', step: identifyQuestion })
	expect(step.screen).toEqual({ kind: 'step', question: identifyQuestion, from: null })
	expect(step.last).toEqual(momentOf(identifyQuestion))
	const open = reducer(step, { type: 'open' })
	expect(open.screen).toEqual({ kind: 'question', question: identifyQuestion, busy: false })
})

test('the next question in the same match moves on from where the last one was asked', () => {
	const first = reducer(watching(), { type: 'arrived', step: identifyQuestion })
	const second = reducer(first, { type: 'arrived', step: { ...identifyQuestion, pack_id: 'next' } })
	expect(second.screen).toMatchObject({ kind: 'step', from: momentOf(identifyQuestion) })
})

test('a question in a new match starts from kick-off again', () => {
	const first = reducer(watching(), { type: 'arrived', step: identifyQuestion })
	const later = reducer(first, { type: 'arrived', step: { ...predictQuestion, match_number: 2 } })
	expect(later.screen).toMatchObject({ kind: 'step', from: null })
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

test('full time shows the summary and forgets where the last question was', () => {
	const first = reducer(watching(), { type: 'arrived', step: identifyQuestion })
	const end = reducer(first, { type: 'arrived', step: fullTime })
	expect(end.screen).toEqual({ kind: 'full_time', summary: fullTime })
	expect(end.last).toBeNull()
})

test('a failure keeps what to retry', () => {
	const open = reducer(reducer(watching(), { type: 'arrived', step: identifyQuestion }), { type: 'open' })
	const retry = { kind: 'answer', question: identifyQuestion, key: 'A' } as const
	const failed = reducer(open, { type: 'failed', message: 'offline', retry })
	expect(failed.screen).toEqual({ kind: 'error', message: 'offline', retry })
	expect(failed.viewer).toBe('lily')
})

test('forgetting the viewer goes back to an empty name form', () => {
	const state = reducer(watching(), { type: 'forget', message: 'That record has gone.' })
	expect(state.viewer).toBeNull()
	expect(state.screen).toEqual({ kind: 'welcome', status: null, error: 'That record has gone.', name: '' })
})

test('the wide-screen header names the match being watched', () => {
	expect(matchHeader({ kind: 'step', question: identifyQuestion, from: null })).toEqual({
		title: 'Ripon Wardens v Ludlow Ferrymen',
		clock: '13:59'
	})
	expect(matchHeader({ kind: 'full_time', summary: fullTime })).toEqual({
		title: 'Ripon Wardens 2–1 Ludlow Ferrymen',
		clock: 'Full time'
	})
	expect(matchHeader({ kind: 'loading', message: '…' })).toBeNull()
})
