import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { finishedStatus, newStatus, startStatus } from '../../test-fixtures/summaries.ts'
import Welcome from './index.tsx'

const handlers = () => ({ onStart: vi.fn(), onWatch: vi.fn(), onChangeName: vi.fn(), onChangeTeam: vi.fn() })

test('the name is sent lower-cased and trimmed', async () => {
	const on = handlers()
	render(<Welcome status={null} error={null} defaultName="" {...on} />)
	await userEvent.type(screen.getByLabelText('Your name'), ' Lily{Enter}')
	expect(on.onStart).toHaveBeenCalledWith('lily')
})

test('an empty name sends nothing', async () => {
	const on = handlers()
	render(<Welcome status={null} error={null} defaultName="" {...on} />)
	await userEvent.click(screen.getByRole('button', { name: 'Start' }))
	expect(on.onStart).not.toHaveBeenCalled()
})

test('a refused name shows the reason beside the field', () => {
	render(<Welcome status={null} error="Only lower-case letters" defaultName="lily!" {...handlers()} />)
	expect(screen.getByRole('alert')).toHaveTextContent('Only lower-case letters')
	expect(screen.getByLabelText('Your name')).toHaveAttribute('aria-invalid', 'true')
	expect(screen.getByLabelText('Your name')).toHaveValue('lily!')
})

test('a found viewer sees the next match and a bar per concept', async () => {
	const on = handlers()
	render(<Welcome status={startStatus} error={null} defaultName="lily" {...on} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Welcome, lily')
	expect(screen.getByText(/Ripon Wardens v Ludlow Ferrymen/)).toHaveTextContent('Match 1 of 3')
	expect(screen.getAllByRole('meter')).toHaveLength(2)
	await userEvent.click(screen.getByRole('button', { name: 'Watch match 1' }))
	expect(on.onWatch).toHaveBeenCalledOnce()
})

test('a viewer who has watched every match is told so and can start again', () => {
	render(<Welcome status={finishedStatus} error={null} defaultName="lily" {...handlers()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('All three matches watched')
	expect(screen.queryByRole('button', { name: /Watch match/ })).toBeNull()
	expect(screen.getByRole('button', { name: 'Start again with another name' })).toBeInTheDocument()
})

test('the viewer sees their team and can change it until they have answered', async () => {
	const on = handlers()
	const { rerender } = render(<Welcome status={startStatus} error={null} defaultName="lily" {...on} />)
	expect(screen.getByText(/Your team:/)).toHaveTextContent('Your team: Ripon Wardens')
	await userEvent.click(screen.getByRole('button', { name: 'Change' }))
	expect(on.onChangeTeam).toHaveBeenCalledOnce()

	rerender(<Welcome status={{ ...startStatus, can_choose_club: false }} error={null} defaultName="lily" {...on} />)
	expect(screen.queryByRole('button', { name: 'Change' })).toBeNull()

	rerender(<Welcome status={newStatus} error={null} defaultName="lily" {...on} />)
	expect(screen.queryByText(/Your team:/)).toBeNull()
})
