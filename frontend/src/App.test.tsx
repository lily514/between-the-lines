import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App.tsx'
import { identifyFeedback, identifyQuestion } from './test-fixtures/index.ts'
import { fullTime, startStatus } from './test-fixtures/summaries.ts'

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
		'/answers': [reply(200, identifyFeedback)]
	})
	const user = userEvent.setup()
	render(<App />)

	await user.type(screen.getByLabelText('Your name'), 'lily{Enter}')
	await user.click(await screen.findByRole('button', { name: 'Watch match 1' }))

	await user.click(await screen.findByRole('button', { name: 'See the question' }))
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(identifyQuestion.text)
	await user.keyboard('1{Enter}')

	expect(await screen.findByRole('heading', { name: 'Right read.' })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'Back to the match' }))

	expect(await screen.findByRole('heading', { name: /Ripon Wardens 2–1 Ludlow Ferrymen/ })).toHaveFocus()
	expect(localStorage.getItem('btl.viewer')).toBe('lily')
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
