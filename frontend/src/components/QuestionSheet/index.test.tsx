import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { counterQuestion, identifyQuestion, predictQuestion } from '../../test-fixtures/index.ts'
import QuestionSheet from './index.tsx'

const lockInButton = () => screen.getByRole('button', { name: /lock in/i })

test('a live predict question shows the freeze-frame, the options on the pitch and no path', () => {
	render(<QuestionSheet question={predictQuestion} onLockIn={vi.fn()} />)
	expect(screen.getByText('Your read')).toBeInTheDocument()
	expect(screen.getByText('32:45 · 1–0')).toBeInTheDocument()
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(predictQuestion.text)
	expect(screen.getByText(/Freeze-frame\. The match carries on/)).toBeInTheDocument()
	expect(screen.getAllByRole('radio')).toHaveLength(3)
	expect(screen.getByTestId('pitch-options').querySelectorAll('path')).toHaveLength(3)
	expect(screen.queryByTestId('pitch-path')).toBeNull()
})

test('a review question says where play is now and shows the play’s path', () => {
	render(<QuestionSheet question={identifyQuestion} onLockIn={vi.fn()} />)
	expect(screen.getByText('Dead ball · free kick')).toBeInTheDocument()
	expect(screen.getByText('13:59')).toBeInTheDocument()
	expect(screen.getByText(/This already happened/)).toBeInTheDocument()
	expect(screen.getByTestId('pitch-path')).toBeInTheDocument()
	expect(screen.queryByTestId('pitch-options')).toBeNull()
})

test('a review question’s time is not repeated when the question already gives it', () => {
	render(<QuestionSheet question={identifyQuestion} onLockIn={vi.fn()} />)
	expect(identifyQuestion.text).toContain(identifyQuestion.occurred.clock)
	expect(screen.queryByText(/Earlier, at/)).toBeNull()
})

test('a review question whose wording leaves out the time gets an “earlier at” line', () => {
	const reworded = { ...counterQuestion, text: 'What did they do after losing the ball?' }
	render(<QuestionSheet question={reworded} onLockIn={vi.fn()} />)
	expect(screen.getByText(/Earlier, at/)).toHaveTextContent(`Earlier, at ${counterQuestion.occurred.clock}`)
})

test('focus moves to the question when the sheet opens', () => {
	render(<QuestionSheet question={predictQuestion} onLockIn={vi.fn()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveFocus()
})

test('lock in stays disabled until a pick, then locks in that pick', async () => {
	const user = userEvent.setup()
	const onLockIn = vi.fn()
	render(<QuestionSheet question={predictQuestion} onLockIn={onLockIn} />)
	expect(lockInButton()).toHaveAttribute('aria-disabled', 'true')
	expect(lockInButton()).toHaveTextContent('Pick an answer to lock in')
	await user.click(lockInButton())
	expect(onLockIn).not.toHaveBeenCalled()

	await user.click(screen.getByRole('radio', { name: /^B/ }))
	expect(lockInButton()).toHaveAttribute('aria-disabled', 'false')
	expect(lockInButton()).toHaveTextContent('Lock in B')
	await user.click(lockInButton())
	expect(onLockIn).toHaveBeenCalledWith('B')
})

test('number keys pick an option and Enter locks it in', async () => {
	const user = userEvent.setup()
	const onLockIn = vi.fn()
	render(<QuestionSheet question={identifyQuestion} onLockIn={onLockIn} />)
	await user.keyboard('3')
	expect(screen.getByRole('radio', { name: /^C/ })).toHaveAttribute('aria-checked', 'true')
	await user.keyboard('{Enter}')
	expect(onLockIn).toHaveBeenCalledTimes(1)
	expect(onLockIn).toHaveBeenCalledWith('C')
})

test('Enter does nothing before a pick', async () => {
	const user = userEvent.setup()
	const onLockIn = vi.fn()
	render(<QuestionSheet question={identifyQuestion} onLockIn={onLockIn} />)
	await user.keyboard('{Enter}')
	expect(onLockIn).not.toHaveBeenCalled()
})

test('while the answer is sent, the pick can’t change and lock in says so', async () => {
	const user = userEvent.setup()
	render(<QuestionSheet question={identifyQuestion} onLockIn={vi.fn()} busy />)
	await user.keyboard('1')
	expect(screen.getByRole('radio', { name: /^A/ })).toHaveAttribute('aria-checked', 'false')
	expect(screen.getByRole('button', { name: 'Locking in…' })).toHaveAttribute('aria-disabled', 'true')
})

test('long labels are laid out as rows, short ones as three columns', () => {
	const { unmount } = render(<QuestionSheet question={predictQuestion} onLockIn={vi.fn()} />)
	expect(screen.getByRole('radiogroup')).toHaveClass('answer-group--rows')
	unmount()
	render(<QuestionSheet question={identifyQuestion} onLockIn={vi.fn()} />)
	expect(screen.getByRole('radiogroup')).toHaveClass('answer-group--columns')
})
