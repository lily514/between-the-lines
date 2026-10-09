import { answer, ApiError, getStatus, nextStep, startViewer } from './client'

const reply = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const mockFetch = (response: Response) => vi.spyOn(globalThis, 'fetch').mockResolvedValue(response)

const sentTo = (spy: ReturnType<typeof mockFetch>) => {
	const [path, init] = spy.mock.calls[0] ?? []
	return { path, init }
}

const sentBody = (spy: ReturnType<typeof mockFetch>): unknown => JSON.parse(sentTo(spy).init?.body as string)

test('starting a viewer posts their name', async () => {
	const spy = mockFetch(reply(200, { viewer_id: 'lily' }))
	await startViewer('lily')
	const { path, init } = sentTo(spy)
	expect(path).toBe('/api/viewers')
	expect(init?.method).toBe('POST')
	expect(sentBody(spy)).toEqual({ viewer_id: 'lily' })
})

test('a seed is sent only when given', async () => {
	const spy = mockFetch(reply(200, {}))
	await startViewer('lily', 7)
	expect(sentBody(spy)).toEqual({ viewer_id: 'lily', seed: 7 })
})

test('status is a plain get', async () => {
	const spy = mockFetch(reply(200, { viewer_id: 'lily' }))
	await getStatus('lily')
	const { path, init } = sentTo(spy)
	expect(path).toBe('/api/viewers/lily')
	expect(init?.method).toBeUndefined()
})

test('the next step can be a question or full time', async () => {
	mockFetch(reply(200, { kind: 'full_time', questions: 5 }))
	const step = await nextStep('lily')
	expect(step.kind).toBe('full_time')
})

test('an answer sends the question it answers', async () => {
	const spy = mockFetch(reply(200, { correct: true }))
	await answer('lily', 'abc123', 'B')
	expect(sentTo(spy).path).toBe('/api/viewers/lily/answers')
	expect(sentBody(spy)).toEqual({ pack_id: 'abc123', key: 'B' })
})

test('viewer names are escaped in the path', async () => {
	const spy = mockFetch(reply(200, {}))
	await getStatus('a/b')
	expect(sentTo(spy).path).toBe('/api/viewers/a%2Fb')
})

test('a stale question gives an error with its status and message', async () => {
	mockFetch(reply(409, { detail: "that isn't the question waiting to be answered" }))
	const error = await answer('lily', 'old', 'A').catch((caught: unknown) => caught)
	expect(error).toBeInstanceOf(ApiError)
	expect(error).toMatchObject({ status: 409, message: "that isn't the question waiting to be answered" })
})

test('validation errors are joined into one message', async () => {
	mockFetch(reply(422, { detail: [{ msg: 'bad name' }, { msg: 'too long' }] }))
	await expect(startViewer('BAD')).rejects.toMatchObject({ status: 422, message: 'bad name; too long' })
})

test('a reply that is not JSON falls back to the status text', async () => {
	mockFetch(new Response('oops', { status: 500, statusText: 'Internal Server Error' }))
	await expect(getStatus('lily')).rejects.toMatchObject({ status: 500, message: 'Internal Server Error' })
})
