import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { MatchSummary, Status } from '../../api/client.ts'
import { matchesAfterOne, matchesInProgress } from '../../test-fixtures/index.ts'
import { startStatus } from '../../test-fixtures/summaries.ts'
import Matches from './index.tsx'
import { featured } from './index.support.ts'

const show = (matches: MatchSummary[], status: Status = startStatus) => {
	const handlers = {
		onWatch: vi.fn(),
		onRejoin: vi.fn(),
		onChangeTeam: vi.fn(),
		onMap: vi.fn(),
		onReport: vi.fn(),
		onStartOver: vi.fn()
	}
	render(<Matches status={status} matches={matches} {...handlers} />)
	return handlers
}

test('a match part-way through leads, with the score at the last answer and Rejoin', async () => {
	const { onRejoin } = show(matchesInProgress)
	const card = screen.getByRole('region', { name: 'Match part-way through' })
	expect(within(card).getByText('at 12:15')).toBeInTheDocument()
	expect(within(card).getByText('0–0')).toBeInTheDocument()
	expect(within(card).getByText('You')).toBeInTheDocument()
	await userEvent.click(within(card).getByRole('button', { name: 'Rejoin the match' }))
	expect(onRejoin).toHaveBeenCalledOnce()
})

test('after a match, the next one leads with its date, and the finished one is listed earlier', async () => {
	const { onWatch, onReport } = show(matchesAfterOne)
	const next = screen.getByRole('region', { name: 'Next match' })
	expect(within(next).getByText(/Next match · Matchday 2/)).toBeInTheDocument()
	expect(within(next).getByText('Sat 31 Oct · kick-off')).toBeInTheDocument()
	await userEvent.click(within(next).getByRole('button', { name: 'See who’s playing' }))
	expect(onWatch).toHaveBeenCalledOnce()
	const earlier = screen.getByRole('region', { name: 'Earlier' })
	expect(within(earlier).getByText('Ripon Wardens 1–0 Truro Otters')).toBeInTheDocument()
	await userEvent.click(within(earlier).getByRole('button', { name: 'Report, matchday 1' }))
	expect(onReport).toHaveBeenCalledWith(1)
})

test('progress shows each concept asked now with its level in words and icon, or what it unlocks after', async () => {
	const { onMap } = show(matchesAfterOne)
	const progress = screen.getByRole('region', { name: 'Your progress' })
	expect(within(progress).getByText('2 concepts asked now')).toBeInTheDocument()
	const level = within(progress).getByText('Getting there')
	expect(level.querySelector('.level-icon')?.getAttribute('data-band')).toBe('getting_there')
	expect(within(progress).getByText('Unlocks after Tackles and turnovers')).toBeInTheDocument()
	await userEvent.click(within(progress).getByRole('button', { name: 'See your full map' }))
	expect(onMap).toHaveBeenCalledOnce()
})

test('with every match watched, there is nothing to lead with', () => {
	const done = matchesAfterOne.map(match => ({ ...match, state: 'finished' as const }))
	expect(featured(done)).toBeNull()
	show(done, { ...startStatus, finished: true })
	expect(screen.getByText('All 3 matches watched')).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'Start again with new matches' })).toBeInTheDocument()
})
