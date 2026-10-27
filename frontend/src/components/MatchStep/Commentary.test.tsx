import { act, render, screen } from '@testing-library/react'
import { counterQuestion, identifyQuestion, predictQuestion } from '../../test-fixtures/index.ts'
import Commentary from './Commentary.tsx'
import { clockAt, heardAt, matchClock, runMs, timeLeft } from './Commentary.support.ts'

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

test('the listener hears who is on the ball, and the spells so far newest first', () => {
	const heard = heardAt(counter, 152)
	expect(heard.onBall).toEqual({ side: 'home', touch: counter.spells[2]?.touches[0] })
	expect(heard.log.map(line => [line.clock, line.side, line.names])).toEqual([
		['02:30', 'home', ['Fonbeira']],
		['01:36', 'away', ['Lindqvist', 'Ferreiro']],
		['00:00', 'home', ['Miloković', 'Escorrieta', 'Hafkamp']]
	])
})

test('a name is not said twice in a row, and the log keeps the last four spells', () => {
	const touch = (at: number, player: string) => ({ at, player, surname: player, number: 1 })
	const spells = Array.from({ length: 6 }, (_, i) => ({
		side: i % 2 === 0 ? ('home' as const) : ('away' as const),
		touches: [touch(i * 10, `P${String(i)}`), touch(i * 10 + 1, `P${String(i)}`), touch(i * 10 + 2, 'Q')]
	}))
	const heard = heardAt({ start: 0, end: 100, names_until: 100, spells }, 100)
	expect(heard.log.map(line => line.index)).toEqual([5, 4, 3, 2])
	expect(heard.log[0]?.names).toEqual(['P5', 'Q'])
})

test('play after the moment a saved question is about goes unnamed', () => {
	expect(heardAt(identify, identify.names_until - 1).onBall).not.toBeNull()
	expect(heardAt(identify, identify.names_until + 1).onBall).toBeNull()
	expect(heardAt(identify, identify.names_until + 1).log).toHaveLength(2)
})

test('the clock runs from where the viewer left off to the next question', () => {
	vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance'] })
	try {
		render(<Commentary play={counter} home="Ripon Wardens" away="Ludlow Ferrymen" />)
		expect(screen.getByRole('timer', { name: 'Match clock' })).toHaveTextContent('00:00')
		expect(screen.getByText('Next question in 3:39')).toBeInTheDocument()
		act(() => {
			vi.advanceTimersByTime(runMs(counter) / 2)
		})
		expect(screen.getByRole('timer')).toHaveTextContent(/^01:4[89]$/)
		expect(screen.getByText(/on the ball:/)).toHaveTextContent('Ludlow Ferrymen on the ball: #10 Ferreiro')
		act(() => {
			vi.advanceTimersByTime(runMs(counter))
		})
		expect(screen.getByRole('timer')).toHaveTextContent('03:38')
		expect(screen.getByText('Question time')).toBeInTheDocument()
		expect(screen.getByText('Play goes on.')).toBeInTheDocument()
	} finally {
		vi.useRealTimers()
	}
})

test('given a slot in the stream view, the commentary shows there too, and the panel keeps it for screen readers', () => {
	const slot = document.createElement('div')
	document.body.append(slot)
	try {
		render(<Commentary play={counter} home="Ripon Wardens" away="Ludlow Ferrymen" streamSlot={slot} />)
		expect(slot).toHaveTextContent(/^00:00Next question in 3:39/)
		expect(slot.querySelector('.commentary__on-ball')).not.toBeNull()
		expect(screen.getAllByRole('timer')).toHaveLength(1)
		expect(screen.getByRole('timer', { name: 'Match clock' }).closest('.commentary')).toHaveClass(
			'commentary--streamed'
		)
	} finally {
		slot.remove()
	}
})
