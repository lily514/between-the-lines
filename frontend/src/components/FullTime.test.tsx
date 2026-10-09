import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { fullTime, lastFullTime } from '../test-fixtures/summaries.ts'
import FullTime from './FullTime.tsx'

test('full time shows the score, the questions asked and each concept from kick-off to now', () => {
	render(<FullTime summary={fullTime} onNext={vi.fn()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Ripon Wardens 2–1 Ludlow Ferrymen')
	expect(screen.getByRole('heading', { level: 2 })).toHaveFocus()
	expect(screen.getByText(/this match/)).toHaveTextContent('1 question this match.')
	expect(screen.getByText(/Line-breaking passes:/)).toHaveTextContent('Line-breaking passes: 15% → 42%')
	expect(screen.getAllByRole('meter')).toHaveLength(2)
})

test('the button goes on to the next match', async () => {
	const onNext = vi.fn()
	render(<FullTime summary={fullTime} onNext={onNext} />)
	await userEvent.click(screen.getByRole('button', { name: 'On to match 2' }))
	expect(onNext).toHaveBeenCalledOnce()
})

test('after the last match the viewer is told they have watched them all', () => {
	render(<FullTime summary={lastFullTime} onNext={vi.fn()} />)
	expect(screen.getByText('You’ve watched all three matches.')).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'See where you stand' })).toBeInTheDocument()
})
