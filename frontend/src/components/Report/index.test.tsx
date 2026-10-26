import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { reportFullTime, reportHalftime } from '../../test-fixtures/index.ts'
import Report from './index.tsx'
import { byStrand, resultLine } from './index.support.ts'

const show = (report = reportFullTime) => {
	const handlers = { onContinue: vi.fn(), onMap: vi.fn() }
	render(<Report report={report} {...handlers} />)
	return handlers
}

test('the full-time report leads with the score and the result from the viewer’s side', () => {
	show()
	expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Ripon Wardens 1–0 Truro Otters')
	expect(screen.getByRole('heading', { level: 2 })).toHaveFocus()
	expect(resultLine(reportFullTime)).toBe('Your team, Ripon Wardens, won 1–0.')
	expect(within(screen.getByRole('list', { name: 'Goals' })).getAllByRole('listitem')).toHaveLength(1)
})

test('the scout’s note and every concept asked now show, with Chances coming later', () => {
	show()
	expect(screen.getByText(reportFullTime.note)).toBeInTheDocument()
	const asked = screen.getByRole('region', { name: 'What you’re being asked' })
	expect(within(asked).getAllByRole('meter')).toHaveLength(5)
	expect(within(asked).getByText(/Chances concepts are coming later/)).toBeInTheDocument()
	expect(byStrand(reportFullTime).map(strand => strand.concepts.length)).toEqual([1, 1, 0, 3])
})

test('each answer says right or not in words, with a mark that isn’t colour alone', () => {
	show()
	const answers = screen.getByRole('region', { name: 'Questions this match' })
	expect(within(answers).getByText((_, element) => element?.textContent === '1 of 5 right.')).toBeInTheDocument()
	expect(within(answers).getAllByText('Right read')).toHaveLength(1)
	expect(within(answers).getAllByText('Not this one')).toHaveLength(4)
})

test('halftime goes on to the second half, full time back to Matches, and both open the map', async () => {
	const half = show(reportHalftime)
	expect(screen.getByText('Questions this half')).toBeInTheDocument()
	await userEvent.click(screen.getByRole('button', { name: 'See your full map' }))
	await userEvent.click(screen.getByRole('button', { name: 'Ready for the second half' }))
	expect(half.onMap).toHaveBeenCalledOnce()
	expect(half.onContinue).toHaveBeenCalledOnce()
})

test('the radar has a table of the same values, and an empty strand reads Not yet', () => {
	show()
	const table = screen.getByRole('table', { name: 'Your scouting report by strand' })
	const chances = within(table).getByRole('row', { name: /Chances/ })
	expect(within(chances).getAllByText('Not yet')).toHaveLength(2)
	expect(within(table).getByRole('row', { name: /Possession/ })).toHaveTextContent('15%')
})
