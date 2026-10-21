import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { clubs } from '../../test-fixtures/summaries.ts'
import PickTeam from './index.tsx'

const pick = (chosen: number | null = null, busy = false) => {
	const onChoose = vi.fn()
	render(<PickTeam clubs={clubs} chosen={chosen} suggested={2} busy={busy} onChoose={onChoose} />)
	return onChoose
}

test('the clubs are one radio group, with the heading focused', () => {
	pick()
	expect(screen.getByRole('heading', { name: 'Pick your team' })).toHaveFocus()
	expect(screen.getByRole('radiogroup', { name: 'Pick your team' })).toBeInTheDocument()
	expect(screen.getAllByRole('radio').map(radio => radio.textContent)).toEqual([
		'Ripon WardensRIP',
		'Hexham AnchorsHEX',
		'Alnwick WeaversALN'
	])
})

test('nothing is sent until a team is picked', async () => {
	const onChoose = pick()
	await userEvent.click(screen.getByRole('button', { name: 'Pick a team to continue' }))
	expect(onChoose).not.toHaveBeenCalled()
})

test('a club is picked by click or arrow keys and confirmed', async () => {
	const onChoose = pick()
	const user = userEvent.setup()
	await user.click(screen.getByRole('radio', { name: /Ripon Wardens/ }))
	await user.keyboard('{ArrowDown}')
	expect(screen.getByRole('radio', { name: /Hexham Anchors/ })).toHaveAttribute('aria-checked', 'true')
	expect(screen.getByRole('radio', { name: /Hexham Anchors/ })).toHaveFocus()
	await user.click(screen.getByRole('button', { name: 'Continue with Hexham Anchors' }))
	expect(onChoose).toHaveBeenCalledWith(2)
})

test('pick one for me picks the suggestion, then moves on, and says so', async () => {
	pick()
	const user = userEvent.setup()
	await user.click(screen.getByRole('button', { name: 'Pick one for me' }))
	expect(screen.getByRole('radio', { name: /Hexham Anchors/ })).toHaveAttribute('aria-checked', 'true')
	expect(screen.getByText('Picked Hexham Anchors')).toBeInTheDocument()
	await user.click(screen.getByRole('button', { name: 'Pick one for me' }))
	expect(screen.getByRole('radio', { name: /Alnwick Weavers/ })).toHaveAttribute('aria-checked', 'true')
})

test('a viewer changing team starts from their club, and nothing is sent while busy', async () => {
	const onChoose = pick(3, true)
	expect(screen.getByRole('radio', { name: /Alnwick Weavers/ })).toHaveAttribute('aria-checked', 'true')
	await userEvent.click(screen.getByRole('button', { name: 'Continue with Alnwick Weavers' }))
	expect(onChoose).not.toHaveBeenCalled()
})
