import { act, cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { counterQuestion, identifyQuestion, predictQuestion } from '../../test-fixtures/index.ts'
import Commentary from './Commentary.tsx'
import { clockAt, entrySummary, heardAt, matchClock, runMs, timeLeft, type Teams } from './Commentary.support.ts'
import MatchStats from './MatchStats.tsx'

const counter = counterQuestion.play_by_play
const identify = identifyQuestion.play_by_play

test('the clock reads as the match clock, and time left as minutes and seconds', () => {
	expect(matchClock(0)).toBe('00:00')
	expect(matchClock(4092.9)).toBe('68:12')
	expect(timeLeft(125)).toBe('2:05')
	expect(timeLeft(0.2)).toBe('0:01')
})

test('a run takes 1.5 s a match minute, at most 20 s, and ends on the question’s clock', () => {
	expect(runMs(predictQuestion.play_by_play)).toBeCloseTo(((1965.27 - 1800) / 60) * 1500, 0)
	expect(runMs(identify)).toBe(20_000)
	expect(clockAt(identify, 10_000, 20_000)).toBeCloseTo(identify.end / 2)
	expect(clockAt(identify, 25_000, 20_000)).toBe(identify.end)
	expect(clockAt({ ...identify, start: identify.end }, 0, 0)).toBe(identify.end)
})

const teamsOf = (question: typeof counterQuestion, yours: 'home' | 'away' | null = null): Teams => ({
	home: question.home,
	away: question.away,
	homeCode: question.home_code,
	awayCode: question.away_code,
	yours
})

const hidden = () => {
	const slot = document.createElement('div')
	slot.setAttribute('aria-hidden', 'true')
	document.body.append(slot)
	return slot
}

test('the listener hears who is on the ball, and the feed so far newest first, each entry once it is complete', () => {
	const heard = heardAt(counter, 152)
	expect(heard.onBall).toEqual({ side: 'home', touch: counter.spells[2]?.touches[0] })
	expect(heard.feed.map(entry => [matchClock(entry.at), entry.kind])).toEqual([
		['02:20', 'shot'],
		['02:00', 'foul'],
		['01:36', 'move'],
		['00:00', 'kick_off']
	])
	expect(heardAt(counter, 156).feed[0]?.names).toEqual(['Fonbeira', 'Miloković'])
})

test('the numbers are the latest the server sent by the clock, or its first before that', () => {
	expect(heardAt(counter, 152).stats?.at).toBe(150.3)
	expect(heardAt(counter, 119).stats?.at).toBe(96.2)
	expect(heardAt({ ...counter, stats: counter.stats.slice(1) }, 10).stats?.at).toBe(96.2)
	expect(heardAt({ ...counter, stats: [] }, 10).stats).toBeNull()
})

test('play after the moment a saved question is about goes unnamed', () => {
	expect(heardAt(identify, identify.names_until - 1).onBall).not.toBeNull()
	expect(heardAt(identify, identify.names_until + 1).onBall).toBeNull()
	expect(heardAt(identify, identify.names_until + 1).feed).toHaveLength(2)
})

test('an entry stands alone as its words, or a move as its players in turn', () => {
	const [move, , foul] = predictQuestion.play_by_play.feed.slice().reverse()
	expect(move && entrySummary(move)).toBe('Nowaković → Jankčić → Hafhuis')
	expect(foul && entrySummary(foul)).toBe('Brennhof is booked.')
})

test('the clock runs from where the viewer left off to the next question', () => {
	vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance'] })
	try {
		render(<Commentary play={counter} teams={teamsOf(counterQuestion)} />)
		expect(screen.getByRole('timer', { name: 'Match clock' })).toHaveTextContent('00:00')
		expect(screen.getByText('Next question in 3:39')).toBeInTheDocument()
		act(() => {
			vi.advanceTimersByTime(runMs(counter) / 2)
		})
		expect(screen.getByRole('timer')).toHaveTextContent(/^01:4[89]$/)
		expect(screen.getByText(/passes, in midfield\.$/)).toHaveTextContent('#10 Ferreiro passes, in midfield.')
		expect(screen.getByText('LUD on the ball')).toBeInTheDocument()
		act(() => {
			vi.advanceTimersByTime(runMs(counter))
		})
		expect(screen.getByRole('timer')).toHaveTextContent('03:38')
		expect(screen.getByText('Question time')).toBeInTheDocument()
		expect(screen.getByText('Asked in the panel')).toBeInTheDocument()
		expect(screen.getByText('Play goes on.')).toBeInTheDocument()
	} finally {
		vi.useRealTimers()
	}
})

test('the scorebug shows the score and half as the server counted them, and You on the viewer’s club', () => {
	render(<Commentary play={predictQuestion.play_by_play} teams={teamsOf(predictQuestion, 'away')} />)
	expect(screen.getByLabelText('Score 1 to 0')).toBeInTheDocument()
	expect(screen.getByText('1st half')).toBeInTheDocument()
	expect(screen.getByText('You')).toBeInTheDocument()
	expect(
		screen.getByRole('img', { name: 'Possession: Hexham Anchors 54%, Penrith Sentinels 46%' })
	).toBeInTheDocument()
})

test('given a slot in the stream view, the match feed shows there, and the panel keeps its copy for screen readers', () => {
	const slot = hidden()
	try {
		render(<Commentary play={counter} teams={teamsOf(counterQuestion)} streamSlot={slot} />)
		expect(slot).toHaveTextContent('Stand-in for your TV')
		expect(within(slot).getByText('Match feed')).toBeInTheDocument()
		expect(
			within(slot).getByText('Thirds as seen by the team on the ball, attacking left to right.')
		).toBeInTheDocument()
		expect(screen.getAllByRole('timer')).toHaveLength(1)
		expect(screen.getByRole('timer', { name: 'Match clock' }).closest('.commentary')).toHaveClass(
			'commentary--streamed'
		)
	} finally {
		slot.remove()
	}
})

test('the feed marks a goal with the score after it, and lists a move’s players in turn', () => {
	const slot = hidden()
	try {
		vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance'] })
		render(<Commentary play={predictQuestion.play_by_play} teams={teamsOf(predictQuestion)} streamSlot={slot} />)
		act(() => {
			vi.advanceTimersByTime(runMs(predictQuestion.play_by_play) + 100)
		})
		const goal = within(slot).getByText('Hafhuis scores.').closest('li')
		expect(goal).toHaveClass('feed-list__entry--goal')
		expect(goal).toHaveTextContent('HEX 1 – 0 PEN')
		const entries = within(slot).getAllByRole('listitem', { hidden: true })
		expect(entries.some(entry => entry.textContent.includes('Nowaković → Jankčić → Hafhuis'))).toBe(true)
		expect(within(slot).getByText('Start of the match')).toBeInTheDocument()
	} finally {
		vi.useRealTimers()
		slot.remove()
	}
})

test('earlier notes open as a sheet with the numbers and the whole feed, and close again', async () => {
	const user = userEvent.setup()
	render(<Commentary play={predictQuestion.play_by_play} teams={teamsOf(predictQuestion)} />)
	await user.click(screen.getByRole('button', { name: 'Earlier notes and stats' }))
	const sheet = screen.getByRole('dialog', { name: 'Earlier notes' })
	expect(within(sheet).getByRole('list', { name: 'Match stats' })).toBeInTheDocument()
	expect(within(sheet).getByRole('heading', { level: 3, name: 'Match feed' })).toBeInTheDocument()
	expect(within(sheet).getByText('Brennhof is booked.')).toBeInTheDocument()
	await user.click(within(sheet).getByRole('button', { name: 'Close' }))
	expect(screen.queryByRole('dialog')).toBeNull()
})

test('the numbers show home and away for each count, and red cards only once there is one', () => {
	const { stats } = predictQuestion.play_by_play
	const first = stats[0]
	if (first === undefined) throw new Error('no stats')
	render(<MatchStats stats={first} teams={teamsOf(predictQuestion)} />)
	const cards = within(screen.getByRole('list', { name: 'Match stats' })).getAllByRole('listitem')
	expect(cards.map(card => card.textContent)).toEqual([
		'ShotsHEX 6PEN 4',
		'CornersHEX 3PEN 2',
		'FoulsHEX 5PEN 7',
		'Yellow cardsHEX 1PEN 2'
	])
	cleanup()
	render(<MatchStats stats={{ ...first, away: { ...first.away, red_cards: 1 } }} teams={teamsOf(predictQuestion)} />)
	expect(screen.getByText('Red cards')).toBeInTheDocument()
})
