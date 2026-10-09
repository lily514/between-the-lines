import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import AnswerGroup from './AnswerGroup.tsx'
import type { Outcome } from './AnswerGroup.support.ts'

const choices = [
	{ key: 'A', label: 'None' },
	{ key: 'B', label: 'One' },
	{ key: 'C', label: 'Two' }
]

const Picking = () => {
	const [selected, setSelected] = useState<string | null>(null)
	return <AnswerGroup label="Your answer" choices={choices} selected={selected} onSelect={setSelected} />
}

test('the group is one tab stop, and arrow keys move and pick', async () => {
	const user = userEvent.setup()
	render(<Picking />)
	const [a, b, c] = screen.getAllByRole('radio')
	expect(a).toHaveAttribute('tabindex', '0')
	expect(b).toHaveAttribute('tabindex', '-1')

	await user.tab()
	expect(a).toHaveFocus()
	await user.keyboard('{ArrowRight}')
	expect(b).toHaveFocus()
	expect(b).toHaveAttribute('aria-checked', 'true')
	expect(b).toHaveAttribute('tabindex', '0')
	await user.keyboard('{ArrowLeft}{ArrowLeft}')
	expect(c).toHaveFocus()
	expect(c).toHaveAttribute('aria-checked', 'true')
})

test('a selected tile shows a mark as well as a colour', async () => {
	const user = userEvent.setup()
	render(<Picking />)
	await user.click(screen.getByRole('radio', { name: /One/ }))
	const picked = screen.getByRole('radio', { name: /One/ })
	expect(picked).toHaveClass('answer-tile--selected')
	expect(picked.querySelector('.answer-tile__dot')).not.toBeNull()
})

test('after a wrong pick, the answer and the pick each show an icon and a word', () => {
	const outcome: Outcome = { correct: 'B', chosen: 'C' }
	render(<AnswerGroup label="Your answer" choices={choices} selected="C" onSelect={vi.fn()} outcome={outcome} />)
	const answer = screen.getByRole('radio', { name: /One/ })
	const pick = screen.getByRole('radio', { name: /Two/ })
	const other = screen.getByRole('radio', { name: /None/ })

	expect(answer).toHaveClass('answer-tile--correct')
	expect(answer).toHaveTextContent('Answer')
	expect(answer.querySelector('.answer-tile__icon')).not.toBeNull()
	expect(pick).toHaveClass('answer-tile--incorrect')
	expect(pick).toHaveTextContent('Your pick')
	expect(pick.querySelector('.answer-tile__icon')).not.toBeNull()
	expect(pick).toHaveAttribute('aria-checked', 'true')
	expect(other).toHaveClass('answer-tile--missed')
	expect(other).toHaveAttribute('aria-checked', 'false')
})

test('after the reveal the pick can’t change', async () => {
	const user = userEvent.setup()
	const onSelect = vi.fn()
	render(
		<AnswerGroup
			label="Your answer"
			choices={choices}
			selected="B"
			onSelect={onSelect}
			outcome={{ correct: 'B', chosen: 'B' }}
		/>
	)
	await user.click(screen.getByRole('radio', { name: /None/ }))
	expect(onSelect).not.toHaveBeenCalled()
	expect(screen.getByRole('radio', { name: /One/ })).toHaveClass('answer-tile--correct')
	expect(screen.getByRole('radio', { name: /One/ })).toHaveAttribute('aria-checked', 'true')
})
