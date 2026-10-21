import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { TeamSheet as TeamSheetData } from '../../api/client.ts'
import { sheetStage1, sheetStage2, sheetStage3 } from '../../test-fixtures/index.ts'
import TeamSheet from './index.tsx'

const show = (sheet: TeamSheetData, canChangeTeam = false) => {
	const on = { onKickOff: vi.fn(), onChangeTeam: vi.fn() }
	const view = render(<TeamSheet sheet={sheet} canChangeTeam={canChangeTeam} {...on} />)
	return { on, view }
}

test('a beginner sees both elevens, their team first, in plain words', async () => {
	const { on } = show(sheetStage1, true)
	expect(screen.getByRole('heading', { name: "Who's playing" })).toHaveFocus()
	const [yours, theirs] = screen.getAllByRole('article')
	if (yours === undefined || theirs === undefined) throw new Error('no cards')
	expect(within(yours).getByRole('heading', { level: 3 })).toHaveTextContent('Ripon WardensYou')
	expect(within(theirs).getByRole('heading', { level: 3 })).toHaveTextContent('Truro Otters')
	expect(within(yours).getAllByRole('listitem')).toHaveLength(11)
	expect(
		within(yours)
			.getAllByRole('heading', { level: 4 })
			.map(h => h.textContent)
	).toEqual(['Goalkeeper', 'Defenders', 'Midfielders', 'Forwards'])
	expect(within(yours).getAllByText('Left back')[0]?.closest('p')).toHaveTextContent(
		'Left back: Defends the left side, and joins attacks down it.'
	)
	expect(screen.queryByText('LB')).toBeNull()
	expect(screen.queryByText('Kick-off shape', { exact: false })).toBeNull()
	expect(screen.getByText('Get to level 2 in any concept to see the formation.')).toBeInTheDocument()

	await userEvent.click(screen.getByRole('button', { name: 'Not your team? Change it' }))
	expect(on.onChangeTeam).toHaveBeenCalledOnce()
	await userEvent.click(screen.getByRole('button', { name: 'Kick off' }))
	expect(on.onKickOff).toHaveBeenCalledOnce()
})

test('the key explains discs, rings, the viewer’s team and shirt numbers', () => {
	show(sheetStage1)
	const key = screen.getByRole('list', { name: 'Key' })
	expect(
		within(key)
			.getAllByRole('listitem')
			.map(item => item.textContent)
	).toEqual([
		'7Filled disc: home side',
		'7Ring: away side',
		'YouDashed ring and "You": your team',
		'#Numbers are shirt numbers'
	])
})

test('stage two adds formations, abbreviations and the kick-off shape with the viewer’s team marked', () => {
	const { view } = show(sheetStage2)
	expect(screen.getAllByText('4-4-2')).toHaveLength(2)
	expect(screen.getAllByTitle('Left back')[0]).toHaveTextContent('LB')
	expect(screen.getByText(/Kick-off shape: your team attacks up/)).toBeInTheDocument()
	expect(view.container.querySelectorAll('[data-testid="pitch-yours"]')).toHaveLength(11)
	expect(view.container.querySelector('.pitch__ball')).toBeNull()
	expect(screen.queryByText('Passes completed')).toBeNull()
})

test('stage three shows numbers for players the viewer has seen, and says who they haven’t', () => {
	show(sheetStage3)
	const [yours, theirs] = screen.getAllByRole('article')
	if (yours === undefined || theirs === undefined) throw new Error('no cards')
	expect(within(yours).getAllByText('Passes completed')).toHaveLength(11)
	expect(within(yours).getByText("From the 2 matches of theirs you've watched.")).toBeInTheDocument()
	expect(within(theirs).getAllByText("First time you've seen them")).toHaveLength(11)
	expect(within(theirs).queryByText('0')).toBeNull()
	expect(screen.queryByRole('button', { name: /Change it/ })).toBeNull()
})
