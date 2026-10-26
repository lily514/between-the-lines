import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App.tsx'
import type { MatchSummary } from '../api/client.ts'
import {
	conceptMap,
	identifyFeedback,
	identifyQuestion,
	matchesAfterOne,
	matchesInProgress,
	predictQuestion,
	reportFullTime,
	reportHalftime,
	sheetStage1
} from '../test-fixtures/index.ts'
import { clubs, fullTime, newStatus, startStatus } from '../test-fixtures/summaries.ts'

const reply = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

/** A fake server: each route answers from its own queue of replies, in order. */
const serve = (routes: Record<string, Response[]>) =>
	vi.spyOn(globalThis, 'fetch').mockImplementation(input => {
		const path = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url
		const route = Object.keys(routes).find(key => path.split('?')[0]?.endsWith(key))
		const next = route === undefined ? undefined : routes[route]?.shift()
		return Promise.resolve(next ?? reply(500, { detail: `no reply for ${path}` }))
	})

/** The viewer's matches before they have watched anything. */
const upcoming: MatchSummary[] = matchesInProgress.map(match => ({
	...match,
	state: 'upcoming',
	score: null,
	questions: 0
}))

beforeEach(() => {
	localStorage.clear()
})

test('a new viewer gets a random id, lands on Matches, and plays a question through to full time', async () => {
	const spy = serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus), reply(200, { ...startStatus, match_number: 2 })],
		'/matches': [reply(200, upcoming), reply(200, matchesAfterOne)],
		'/next': [reply(200, identifyQuestion), reply(200, fullTime)],
		'/answers': [reply(200, identifyFeedback)],
		'/team-sheet': [reply(200, sheetStage1)],
		'/report': [reply(200, reportFullTime)]
	})
	const user = userEvent.setup()
	render(<App />)

	await user.click(screen.getByRole('button', { name: 'Continue' }))
	const post = spy.mock.calls.find(([input, init]) => input === '/api/viewers' && init?.method === 'POST')
	expect(JSON.parse(post?.[1]?.body as string)).toEqual({
		viewer_id: expect.stringMatching(/^[0-9a-f]{32}$/) as string
	})
	expect(await screen.findByRole('heading', { name: 'Matches' })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'See who’s playing' }))
	expect(await screen.findByRole('heading', { name: "Who's playing" })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'Kick off' }))

	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(identifyQuestion.text)
	await user.keyboard('1{Enter}')

	expect(await screen.findByRole('heading', { name: 'Right read.' })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'Back to the match' }))

	expect(await screen.findByRole('heading', { name: /Ripon Wardens 1–0 Truro Otters/ })).toHaveFocus()
	expect(screen.getByText('Your team, Ripon Wardens, won 1–0.')).toBeInTheDocument()
	expect(localStorage.getItem('btl.viewer')).toBe('lily')
	await user.click(screen.getByRole('button', { name: 'Done for this match' }))
	expect(await screen.findByRole('heading', { name: 'Matches' })).toBeInTheDocument()
})

test('a remembered viewer comes back to Matches and rejoins the match part-way through', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus)],
		'/matches': [reply(200, matchesInProgress)],
		'/next': [reply(200, identifyQuestion)]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Rejoin the match' }))
	expect(await screen.findByRole('heading', { name: /Play has stopped for a free kick/ })).toBeInTheDocument()
})

test('done for this match goes back to Matches', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus), reply(200, startStatus)],
		'/matches': [reply(200, matchesInProgress), reply(200, matchesInProgress)],
		'/next': [reply(200, identifyQuestion)]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Rejoin the match' }))
	await user.click(await screen.findByRole('button', { name: 'Done for this match' }))
	expect(await screen.findByRole('heading', { name: 'Matches' })).toBeInTheDocument()
})

test('an answer to a question the server is no longer waiting on fetches the one it is', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	const waiting = { ...identifyQuestion, pack_id: 'the-waiting-one', text: 'The question the server is waiting on' }
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus)],
		'/matches': [reply(200, matchesInProgress)],
		'/next': [reply(200, identifyQuestion), reply(200, waiting)],
		'/answers': [reply(409, { detail: 'not the waiting question' })]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Rejoin the match' }))
	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	await user.keyboard('1{Enter}')
	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('The question the server is waiting on')
})

test('the map opens from the header over a question, and Back returns to it as it was', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus)],
		'/matches': [reply(200, matchesInProgress)],
		'/next': [reply(200, identifyQuestion)],
		'/concept-map': [reply(200, conceptMap)]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Rejoin the match' }))
	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	await user.keyboard('2')
	const picked = screen.getByRole('radio', { checked: true })

	await user.click(screen.getByRole('button', { name: 'Curriculum map' }))
	expect(await screen.findByRole('heading', { name: 'Your pitch' })).toHaveFocus()
	expect(screen.queryByRole('radio')).toBeNull()

	await user.click(screen.getByRole('button', { name: 'Close the map and go back to where you were' }))
	expect(screen.getByRole('radio', { checked: true })).toBe(picked)
	expect(screen.getByRole('button', { name: 'Curriculum map' })).toHaveFocus()
})

test('onboarding has no map button, but the welcome opens the whole map', async () => {
	serve({ '/concept-map': [reply(200, conceptMap), reply(200, conceptMap)] })
	const user = userEvent.setup()
	render(<App />)
	expect(screen.queryByRole('button', { name: 'Curriculum map' })).toBeNull()
	await user.click(await screen.findByRole('button', { name: /See all 20 concepts/ }))
	expect(await screen.findByRole('heading', { name: 'Your pitch' })).toBeInTheDocument()
	await user.keyboard('{Escape}')
	expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
})

test('a kept id the API refuses is forgotten, with the reason shown', async () => {
	localStorage.setItem('btl.viewer', 'Edited By Hand')
	serve({ '/api/viewers': [reply(422, { detail: [{ msg: "isn't a valid viewer id" }] })] })
	render(<App />)
	expect(await screen.findByRole('alert')).toHaveTextContent("isn't a valid viewer id")
	expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
	expect(localStorage.getItem('btl.viewer')).toBeNull()
})

test('a failed request offers to try again, and trying again carries on', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus), reply(200, startStatus)],
		'/matches': [reply(503, { detail: 'The server is busy' }), reply(200, matchesInProgress)]
	})
	const user = userEvent.setup()
	render(<App />)
	expect(await screen.findByRole('alert')).toHaveTextContent('The server is busy')
	await user.click(screen.getByRole('button', { name: 'Try again' }))
	expect(await screen.findByRole('heading', { name: 'Matches' })).toBeInTheDocument()
})

test('a record that has gone sends the viewer back to the welcome', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(404, { detail: 'no learner' })],
		'/matches': [reply(404, { detail: 'no learner' })]
	})
	render(<App />)
	expect(await screen.findByText(/That record has gone/)).toBeInTheDocument()
	expect(localStorage.getItem('btl.viewer')).toBeNull()
})

test('starting over asks first, then forgets the viewer', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus)],
		'/matches': [reply(200, upcoming)]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Start over' }))
	expect(localStorage.getItem('btl.viewer')).toBe('lily')
	await user.click(screen.getByRole('button', { name: 'Yes, start over' }))
	expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
	expect(localStorage.getItem('btl.viewer')).toBeNull()
})

test('a new viewer picks a team before anything else, and can change it from Matches', async () => {
	const chosen = { ...startStatus, club: clubs[1] ?? null }
	const spy = serve({
		'/api/viewers': [reply(200, newStatus)],
		'/api/clubs': [reply(200, clubs), reply(200, clubs)],
		'/api/viewers/lily/club': [reply(200, chosen)],
		'/api/viewers/lily': [reply(200, chosen)],
		'/matches': [reply(200, upcoming)]
	})
	const user = userEvent.setup()
	render(<App />)

	await user.click(screen.getByRole('button', { name: 'Continue' }))
	await user.click(await screen.findByRole('radio', { name: /Hexham Anchors/ }))
	await user.click(screen.getByRole('button', { name: 'Continue with Hexham Anchors' }))

	expect(await screen.findByText(/Your team:/)).toHaveTextContent('Hexham Anchors')
	const put = spy.mock.calls.find(([input]) => typeof input === 'string' && input.endsWith('/club'))
	expect(put?.[1]).toMatchObject({ method: 'PUT', body: JSON.stringify({ club: 2 }) })

	await user.click(screen.getByRole('button', { name: 'Change' }))
	expect(await screen.findByRole('radio', { name: /Hexham Anchors/ })).toHaveAttribute('aria-checked', 'true')
})

test('a remembered viewer with no team yet is asked for one', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({ '/api/viewers': [reply(200, newStatus)], '/api/clubs': [reply(200, clubs)] })
	render(<App />)
	expect(await screen.findByRole('heading', { name: 'Pick your team' })).toBeInTheDocument()
})

test('a team refused because watching has started shows Matches with the team settled', async () => {
	serve({
		'/api/viewers': [reply(200, newStatus)],
		'/api/clubs': [reply(200, clubs)],
		'/api/viewers/lily/club': [reply(409, { detail: "the team can't change once you've started watching" })],
		'/api/viewers/lily': [reply(200, { ...startStatus, can_choose_club: false })],
		'/matches': [reply(200, matchesInProgress)]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(screen.getByRole('button', { name: 'Continue' }))
	await user.click(await screen.findByRole('button', { name: 'Pick one for me' }))
	await user.click(screen.getByRole('button', { name: 'Continue with Hexham Anchors' }))
	expect(await screen.findByRole('heading', { name: 'Matches' })).toBeInTheDocument()
	expect(screen.queryByRole('button', { name: 'Change' })).toBeNull()
})

test('the first question of the second half comes after the halftime report', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	const second = { ...predictQuestion, match_number: 1, delivered: { ...predictQuestion.delivered, period: 2 } }
	const spy = serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus)],
		'/matches': [reply(200, matchesInProgress)],
		'/next': [reply(200, second)],
		'/report': [reply(200, reportHalftime)]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Rejoin the match' }))
	expect(await screen.findByText('Half-time')).toBeInTheDocument()
	const asked = spy.mock.calls
		.map(([input]) => (typeof input === 'string' ? input : ''))
		.find(path => path.includes('/report'))
	expect(asked).toBe('/api/viewers/lily/matches/1/report?at=halftime')
	await user.click(screen.getByRole('button', { name: 'Ready for the second half' }))
	expect(await screen.findByRole('heading', { name: /Settled possession/ })).toBeInTheDocument()
})

test('Preferences open from the header over Matches, and a change of pace is saved', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	const spy = serve({
		'/api/viewers': [reply(200, startStatus)],
		'/api/viewers/lily': [reply(200, startStatus), reply(200, startStatus)],
		'/matches': [reply(200, upcoming)],
		'/pace': [reply(200, { ...startStatus, pace: 'rarely' })]
	})
	const user = userEvent.setup()
	render(<App />)
	await screen.findByRole('heading', { name: 'Matches' })
	await user.click(screen.getByRole('button', { name: 'Preferences' }))
	await user.click(await screen.findByRole('radio', { name: 'Rarely' }))
	expect(await screen.findByRole('radio', { name: 'Rarely' })).toBeChecked()
	const put = spy.mock.calls.find(([input]) => typeof input === 'string' && input.endsWith('/pace'))
	expect(put?.[1]).toMatchObject({ method: 'PUT', body: JSON.stringify({ pace: 'rarely' }) })
	await user.keyboard('{Escape}')
	expect(screen.getByRole('heading', { name: 'Matches' })).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'Preferences' })).toHaveFocus()
})
