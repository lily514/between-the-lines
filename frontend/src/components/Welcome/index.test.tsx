import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { curriculum } from '../../test-fixtures/index.ts'
import Welcome from './index.tsx'
import { askedNow } from './index.support.ts'

const show = (props: Partial<Parameters<typeof Welcome>[0]> = {}) => {
	const handlers = { onStart: vi.fn(), onSeeAll: vi.fn() }
	render(<Welcome curriculum={curriculum} error={null} {...handlers} {...props} />)
	return handlers
}

test('the welcome says what the questions cover, by strand, with the most first', () => {
	show()
	expect(screen.getByRole('heading', { level: 2 })).toHaveFocus()
	expect(screen.getByText(/For now they cover 5 things\./)).toBeInTheDocument()
	const flow = screen.getByRole('region', { name: 'Game flow' })
	expect(within(flow).getByText('3 to start')).toBeInTheDocument()
	expect(within(flow).getByText('Restarts')).toBeInTheDocument()
	expect(within(flow).getByText('Offside')).toBeInTheDocument()
	expect(within(flow).getByText('Fouls and cards')).toBeInTheDocument()
	const chances = screen.getByRole('region', { name: 'Chances' })
	expect(within(chances).getByText('Coming later')).toBeInTheDocument()
	expect(screen.getByText('Getting there')).toBeInTheDocument()
})

test('the strands run from most asked to none', () => {
	expect(askedNow(curriculum).map(group => group.concepts.length)).toEqual([3, 1, 1, 0])
})

test('continue starts, and the link opens the whole map', async () => {
	const { onStart, onSeeAll } = show()
	await userEvent.click(screen.getByRole('button', { name: /See all 20 concepts/ }))
	expect(onSeeAll).toHaveBeenCalledOnce()
	await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
	expect(onStart).toHaveBeenCalledOnce()
})

test('it works before the curriculum has loaded, and shows why starting failed', () => {
	show({ curriculum: null, error: 'The server could not be reached.' })
	expect(screen.getByRole('alert')).toHaveTextContent('The server could not be reached.')
	expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
})
