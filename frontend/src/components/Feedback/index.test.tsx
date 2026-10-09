import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
	counterFeedback,
	counterQuestion,
	identifyFeedback,
	identifyQuestion,
	predictFeedback,
	predictQuestion
} from '../../test-fixtures/index.ts'
import Feedback from './index.tsx'
import { humanise, pickedLine, statTiles } from './index.support.ts'

test('a right answer shows a filled check and the word, and no mix-up', () => {
	render(<Feedback feedback={identifyFeedback} question={identifyQuestion} onContinue={vi.fn()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Right read.')
	expect(screen.getByRole('img', { name: 'Right' })).toBeInTheDocument()
	expect(screen.getByText('Answer')).toBeInTheDocument()
	expect(screen.queryByRole('complementary', { name: 'Common mix-up' })).toBeNull()
	expect(screen.getByText(/^You picked A: One\.$/)).toBeInTheDocument()
})

test('a wrong answer shows a dashed cross, the viewer’s pick and the right one', () => {
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={vi.fn()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Good instinct, not this one.')
	expect(screen.getByRole('img', { name: 'Not this one' })).toBeInTheDocument()
	expect(screen.getByText('Your pick')).toBeInTheDocument()
	expect(screen.getByText('Answer')).toBeInTheDocument()
	expect(screen.getByText('You picked A: Pass to #14 Niels Rosinga. It was C.')).toBeInTheDocument()
})

test('a wrong answer sets the common mix-up aside, with its warning sign and label', () => {
	render(<Feedback feedback={counterFeedback} question={counterQuestion} onContinue={vi.fn()} />)
	const aside = screen.getByRole('complementary', { name: 'Common mix-up' })
	expect(within(aside).getByRole('img', { name: 'Common mix-up' })).toBeInTheDocument()
	expect(aside).toHaveTextContent(`“${counterFeedback.misconception ?? ''}”`)
	expect(screen.getByText(counterFeedback.explanation)).not.toHaveTextContent('mix-up')
})

test('the stat tiles show the pack’s display text exactly', () => {
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={vi.fn()} />)
	const tiles = within(screen.getByLabelText('Computed from match data'))
	expect(tiles.getByText('Lines broken').nextSibling).toHaveTextContent(
		predictFeedback.outcome.lines_broken?.display ?? '?'
	)
	expect(tiles.getByText('Gap').nextSibling).toHaveTextContent(`${predictFeedback.outcome.gap_m?.display ?? '?'} m`)
	expect(tiles.getByText('Chance added').nextSibling).toHaveTextContent(
		predictFeedback.outcome.threat_added?.display ?? '?'
	)
	expect(tiles.queryByText('Receiver')).toBeNull()
})

test('the source line names the match, the action and who wrote the words', () => {
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={vi.fn()} />)
	expect(screen.getByText('Source · match 7003 · action 508 · worded by template')).toBeInTheDocument()
})

test('the learner model’s move is shown as words, numbers and a bar with both thresholds', () => {
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={vi.fn()} />)
	expect(screen.getByText(predictFeedback.update)).toBeInTheDocument()
	const meter = screen.getByRole('meter', { name: 'Line-breaking passes' })
	expect(meter).toHaveAttribute('aria-valuenow', '24')
	expect(meter).toHaveAttribute('aria-valuetext', '43% to 24%. Unlocks the next concept at 80%, mastered at 95%.')
	expect(screen.getByText('80 unlocks next')).toBeInTheDocument()
	expect(screen.getByText('95 mastered')).toBeInTheDocument()
})

test('the real play is drawn as a reveal', () => {
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={vi.fn()} />)
	expect(screen.getByTestId('pitch-path')).toBeInTheDocument()
	expect(screen.getByTestId('pitch-options').querySelectorAll('path')).toHaveLength(3)
})

test('focus moves to the verdict, and the copy is announced politely', () => {
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={vi.fn()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveFocus()
	expect(screen.getByText(predictFeedback.explanation).closest('[aria-live]')).toHaveAttribute('aria-live', 'polite')
})

test('back to the match carries on', async () => {
	const user = userEvent.setup()
	const onContinue = vi.fn()
	render(<Feedback feedback={predictFeedback} question={predictQuestion} onContinue={onContinue} />)
	await user.click(screen.getByRole('button', { name: 'Back to the match' }))
	expect(onContinue).toHaveBeenCalledOnce()
})

test('tiles follow a fixed order, and unknown facts still get a tile with a readable label', () => {
	const withExtra = {
		...counterFeedback,
		outcome: { ...counterFeedback.outcome, passes_before_regain: { value: 2, display: 'two' } }
	}
	expect(statTiles(withExtra).map(s => s.label)).toEqual([
		'Won back in',
		'Players pressing',
		'From goal',
		'Passes before regain'
	])
	expect(humanise('seconds_to_regain')).toBe('Seconds to regain')
})

test('a right pick doesn’t say which was right again', () => {
	expect(pickedLine(identifyFeedback)).toBe('You picked A: One.')
})
