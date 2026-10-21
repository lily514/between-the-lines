import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App.tsx'
import { identifyFeedback, identifyQuestion, sheetStage1 } from '../test-fixtures/index.ts'
import { clubs, fullTime, newStatus, startStatus } from '../test-fixtures/summaries.ts'

const reply = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

/** A fake server: each route answers from its own queue of replies, in order. */
const serve = (routes: Record<string, Response[]>) =>
	vi.spyOn(globalThis, 'fetch').mockImplementation(input => {
		const path = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url
		const route = Object.keys(routes).find(key => path.endsWith(key))
		const next = route === undefined ? undefined : routes[route]?.shift()
		return Promise.resolve(next ?? reply(500, { detail: `no reply for ${path}` }))
	})

beforeEach(() => {
	localStorage.clear()
})

test('a viewer plays from their name through a question and its feedback to full time', async () => {
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/next': [reply(200, identifyQuestion), reply(200, fullTime)],
		'/answers': [reply(200, identifyFeedback)],
		'/team-sheet': [reply(200, sheetStage1), reply(200, { ...sheetStage1, match_number: 2 })]
	})
	const user = userEvent.setup()
	render(<App />)

	await user.type(screen.getByLabelText('Your name'), 'lily{Enter}')
	await user.click(await screen.findByRole('button', { name: 'Watch match 1' }))
	expect(await screen.findByRole('heading', { name: "Who's playing" })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'Kick off' }))

	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(identifyQuestion.text)
	await user.keyboard('1{Enter}')

	expect(await screen.findByRole('heading', { name: 'Right read.' })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'Back to the match' }))

	expect(await screen.findByRole('heading', { name: /Ripon Wardens 2–1 Ludlow Ferrymen/ })).toHaveFocus()
	expect(screen.getByText('Your team, Ripon Wardens, won 2–1.')).toBeInTheDocument()
	expect(localStorage.getItem('btl.viewer')).toBe('lily')

	await user.click(screen.getByRole('button', { name: 'On to match 2' }))
	await screen.findByRole('heading', { name: "Who's playing" })
	expect(document.querySelector('.team-sheet__fixture')).toHaveTextContent(/^Match 2 ·/)
	expect(screen.queryByRole('button', { name: /Change it/ })).toBeNull()
})

test('a remembered viewer goes straight back to the waiting question', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	const spy = serve({ '/api/viewers': [reply(200, startStatus)], '/next': [reply(200, identifyQuestion)] })
	render(<App />)
	expect(await screen.findByRole('heading', { name: /Play has stopped for a free kick/ })).toBeInTheDocument()
	expect(spy).toHaveBeenCalledTimes(2)
})

test('an answer to a question the server is no longer waiting on fetches the one it is', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	const waiting = { ...identifyQuestion, pack_id: 'the-waiting-one', text: 'The question the server is waiting on' }
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/next': [reply(200, identifyQuestion), reply(200, waiting)],
		'/answers': [reply(409, { detail: 'not the waiting question' })]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	await user.keyboard('1{Enter}')
	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('The question the server is waiting on')
})

test('a refused name is shown on the form', async () => {
	serve({ '/api/viewers': [reply(422, { detail: [{ msg: 'Use lower-case letters and digits' }] })] })
	const user = userEvent.setup()
	render(<App />)
	await user.type(screen.getByLabelText('Your name'), 'li ly{Enter}')
	expect(await screen.findByRole('alert')).toHaveTextContent('Use lower-case letters and digits')
	expect(screen.getByLabelText('Your name')).toHaveValue('li ly')
})

test('a failed request offers to try again, and trying again carries on', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({
		'/api/viewers': [reply(200, startStatus)],
		'/next': [reply(503, { detail: 'The server is busy' }), reply(200, identifyQuestion)]
	})
	const user = userEvent.setup()
	render(<App />)
	expect(await screen.findByRole('alert')).toHaveTextContent('The server is busy')
	await user.click(screen.getByRole('button', { name: 'Try again' }))
	expect(await screen.findByRole('heading', { name: /Play has stopped for a free kick/ })).toBeInTheDocument()
})

test('a record that has gone sends the viewer back to the name form', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({ '/api/viewers': [reply(200, startStatus)], '/next': [reply(404, { detail: 'no learner' })] })
	render(<App />)
	expect(await screen.findByText(/That record has gone/)).toBeInTheDocument()
	expect(localStorage.getItem('btl.viewer')).toBeNull()
})

test('the viewer can change their name', async () => {
	localStorage.setItem('btl.viewer', 'lily')
	serve({ '/api/viewers': [reply(200, startStatus)], '/next': [reply(200, identifyQuestion)] })
	const user = userEvent.setup()
	render(<App />)
	await user.click(await screen.findByRole('button', { name: 'Not lily?' }))
	expect(screen.getByLabelText('Your name')).toHaveValue('')
	expect(localStorage.getItem('btl.viewer')).toBeNull()
})

test('a new viewer picks a team before anything else, and can change it from the welcome', async () => {
	const spy = serve({
		'/api/viewers': [reply(200, newStatus)],
		'/api/clubs': [reply(200, clubs), reply(200, clubs)],
		'/api/viewers/lily/club': [reply(200, { ...startStatus, club: clubs[1] })]
	})
	const user = userEvent.setup()
	render(<App />)

	await user.type(screen.getByLabelText('Your name'), 'lily{Enter}')
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

test('a team refused because watching has started shows where the viewer stands', async () => {
	serve({
		'/api/viewers': [reply(200, newStatus)],
		'/api/clubs': [reply(200, clubs)],
		'/api/viewers/lily/club': [reply(409, { detail: "the team can't change once you've started watching" })],
		'/api/viewers/lily': [reply(200, { ...startStatus, can_choose_club: false })]
	})
	const user = userEvent.setup()
	render(<App />)
	await user.type(screen.getByLabelText('Your name'), 'lily{Enter}')
	await user.click(await screen.findByRole('button', { name: 'Pick one for me' }))
	await user.click(screen.getByRole('button', { name: 'Continue with Hexham Anchors' }))
	expect(await screen.findByRole('heading', { name: 'Welcome, lily' })).toBeInTheDocument()
	expect(screen.queryByRole('button', { name: 'Change' })).toBeNull()
})
