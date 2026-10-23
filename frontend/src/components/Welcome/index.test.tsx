import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { finishedStatus, newStatus, startStatus } from '../../test-fixtures/summaries.ts'
import Welcome from './index.tsx'

const handlers = () => ({ onStart: vi.fn(), onWatch: vi.fn(), onStartOver: vi.fn(), onChangeTeam: vi.fn() })

test('a new visitor starts with one button, and no name to type', async () => {
	const on = handlers()
	render(<Welcome status={null} error={null} {...on} />)
	expect(screen.queryByRole('textbox')).toBeNull()
	await userEvent.click(screen.getByRole('button', { name: 'Start' }))
	expect(on.onStart).toHaveBeenCalledOnce()
})

test('a reason starting failed is shown', () => {
	render(<Welcome status={null} error="isn't a valid viewer id" {...handlers()} />)
	expect(screen.getByRole('alert')).toHaveTextContent("isn't a valid viewer id")
})

test('a found viewer sees the next match and a bar per concept, and never their id', async () => {
	const on = handlers()
	render(<Welcome status={startStatus} error={null} {...on} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(/^Welcome$/)
	expect(screen.queryByText(new RegExp(startStatus.viewer_id))).toBeNull()
	expect(screen.getByText(/Ripon Wardens v Ludlow Ferrymen/)).toHaveTextContent('Match 1 of 3')
	expect(screen.getAllByRole('meter')).toHaveLength(2)
	await userEvent.click(screen.getByRole('button', { name: 'Watch match 1' }))
	expect(on.onWatch).toHaveBeenCalledOnce()
})

test('starting over asks first, and keeping going changes nothing', async () => {
	const on = handlers()
	render(<Welcome status={startStatus} error={null} {...on} />)
	await userEvent.click(screen.getByRole('button', { name: 'Start over' }))
	expect(screen.getByRole('group', { name: 'Start over?' })).toHaveTextContent(/can’t be found again/)
	expect(screen.getByRole('button', { name: 'Keep going' })).toHaveFocus()

	await userEvent.click(screen.getByRole('button', { name: 'Keep going' }))
	expect(on.onStartOver).not.toHaveBeenCalled()

	await userEvent.click(screen.getByRole('button', { name: 'Start over' }))
	await userEvent.click(screen.getByRole('button', { name: 'Yes, start over' }))
	expect(on.onStartOver).toHaveBeenCalledOnce()
})

test('a viewer who has watched every match is told so and can start again', () => {
	render(<Welcome status={finishedStatus} error={null} {...handlers()} />)
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('All three matches watched')
	expect(screen.queryByRole('button', { name: /Watch match/ })).toBeNull()
	expect(screen.getByRole('button', { name: 'Start again with new matches' })).toBeInTheDocument()
})

test('the viewer sees their team and can change it until they have answered', async () => {
	const on = handlers()
	const { rerender } = render(<Welcome status={startStatus} error={null} {...on} />)
	expect(screen.getByText(/Your team:/)).toHaveTextContent('Your team: Ripon Wardens')
	await userEvent.click(screen.getByRole('button', { name: 'Change' }))
	expect(on.onChangeTeam).toHaveBeenCalledOnce()

	rerender(<Welcome status={{ ...startStatus, can_choose_club: false }} error={null} {...on} />)
	expect(screen.queryByRole('button', { name: 'Change' })).toBeNull()

	rerender(<Welcome status={newStatus} error={null} {...on} />)
	expect(screen.queryByText(/Your team:/)).toBeNull()
})
