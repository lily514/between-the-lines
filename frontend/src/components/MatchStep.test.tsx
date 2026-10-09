import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { identifyQuestion, predictQuestion } from '../test-fixtures/index.ts'
import MatchStep from './MatchStep.tsx'
import { movedOn, stepHeading, whyNow } from './MatchStep.support.ts'

const stepTo = (question: typeof identifyQuestion, from: string | null = null, onArrive = vi.fn()) =>
	render(
		<MatchStep
			home={question.home}
			away={question.away}
			matchNumber={question.match_number}
			from={from}
			to={question.delivered}
			occurred={question.occurred}
			score={null}
			onArrive={onArrive}
		/>
	)

test('a review question’s step says play has stopped, and why the question comes now', () => {
	stepTo(identifyQuestion)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Play has stopped for a free kick at 13:59')
	expect(screen.getByText('Dead ball · free kick')).toBeInTheDocument()
	expect(screen.getByText('A question about the play at 05:12, saved until play stopped.')).toBeInTheDocument()
	expect(screen.getByText('Kick-off. The match moves on to 13:59.')).toBeInTheDocument()
})

test('a live question’s step is in settled possession', () => {
	stepTo(predictQuestion, '13:59')
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Settled possession at 32:45')
	expect(screen.getByText('Settled possession')).toBeInTheDocument()
	expect(screen.getByText('The match moves on from 13:59 to 32:45.')).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'Make your read' })).toBeInTheDocument()
})

test('focus moves to the step’s heading, and the button arrives at the question', async () => {
	const onArrive = vi.fn()
	stepTo(identifyQuestion, null, onArrive)
	expect(screen.getByRole('heading', { level: 2 })).toHaveFocus()
	await userEvent.click(screen.getByRole('button', { name: 'See the question' }))
	expect(onArrive).toHaveBeenCalledOnce()
})

test('breaks are named as breaks, without a clock', () => {
	const halfTime = { ...identifyQuestion.delivered, phase: 'half-time', restart: null }
	expect(stepHeading(halfTime)).toBe('Half-time')
	expect(movedOn('40:10', halfTime)).toBe('The match moved on from 40:10 to the whistle.')
	expect(whyNow(halfTime, identifyQuestion.occurred)).toContain('05:12')
})
