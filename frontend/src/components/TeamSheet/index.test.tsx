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

const card = () => screen.getByRole('region', { name: 'Chosen player' })
const pitch = () => screen.getByRole('group', { name: /^Kick-off positions/ })

test('a beginner sees both clubs and all 22 starters on the pitch, their team first, with no tags', async () => {
	const { on, view } = show(sheetStage1, true)
	expect(screen.getByRole('heading', { name: "Who's playing" })).toHaveFocus()
	const [yours, theirs] = screen.getAllByRole('article')
	if (yours === undefined || theirs === undefined) throw new Error('no club cards')
	expect(yours).toHaveTextContent('Ripon WardensYouHome, filled discs')
	expect(theirs).toHaveTextContent('Truro OttersAway, rings')
	expect(within(pitch()).getAllByRole('button')).toHaveLength(22)
	expect(pitch()).toHaveAccessibleName(
		'Kick-off positions. Ripon Wardens, your team, filled discs, attacking up from the bottom. Truro Otters, ' +
			'rings, at the top. Each player is a button: choose one to see who they are.'
	)
	expect(view.container.querySelector('[data-testid="your-half"]')).not.toBeNull()
	expect(within(card()).getByRole('heading')).toHaveTextContent('Adama Trafo')
	expect(card()).toHaveTextContent('Ripon Wardens · home · your team')
	expect(card()).toHaveTextContent('Striker Plays furthest forward, closest to goal: there to score.')
	expect(screen.queryByText('ST')).toBeNull()
	expect(screen.queryByText('4-4-2')).toBeNull()
	expect(screen.getByText('Get to level 2 in any concept to see formations and position tags.')).toBeInTheDocument()

	await userEvent.click(screen.getByRole('button', { name: 'Not your team? Change it' }))
	expect(on.onChangeTeam).toHaveBeenCalledOnce()
	await userEvent.click(screen.getByRole('button', { name: 'Kick off' }))
	expect(on.onKickOff).toHaveBeenCalledOnce()
})

test('hovering, tapping or tabbing to a player on the pitch fills the card and marks them chosen', async () => {
	show(sheetStage1)
	const leftBack = within(pitch()).getByRole('button', {
		name: 'Number 5, Dennis Hafkamp, Ripon Wardens, Left back'
	})
	await userEvent.hover(leftBack)
	expect(within(card()).getByRole('heading')).toHaveTextContent('Dennis Hafkamp')
	expect(leftBack).toHaveAttribute('aria-pressed', 'true')

	const keeper = within(pitch()).getByRole('button', { name: /Khaled Mehiri/ })
	await userEvent.click(keeper)
	expect(within(card()).getByRole('heading')).toHaveTextContent('Khaled Mehiri')
	expect(card()).toHaveTextContent('Truro Otters · away')
	expect(card()).toHaveAttribute('aria-live', 'polite')
	expect(leftBack).toHaveAttribute('aria-pressed', 'false')

	keeper.focus()
	await userEvent.tab()
	expect(within(card()).getByRole('heading')).not.toHaveTextContent('Khaled Mehiri')
})

test('the line-ups list chooses the same player as the pitch', async () => {
	show(sheetStage2)
	await userEvent.click(screen.getByText('Both line-ups as a list'))
	const name = 'Number 1, Diogo Marteiro, Bakewell Badgers, Goalkeeper'
	const list = screen.getByRole('region', { name: 'Bakewell Badgers' })
	await userEvent.click(within(list).getByRole('button', { name }))
	expect(within(card()).getByRole('heading')).toHaveTextContent('Diogo Marteiro')
	expect(within(pitch()).getByRole('button', { name })).toHaveAttribute('aria-pressed', 'true')
	expect(within(list).getByRole('button', { name })).toHaveTextContent('1MarteiroGK')
})

test('stage two adds formations and position tags, and says what level three adds', () => {
	show(sheetStage2)
	expect(screen.getAllByText('4-4-2')).toHaveLength(2)
	expect(within(card()).getByTitle('Striker')).toHaveTextContent('ST')
	expect(within(card()).queryByText('Passes completed')).toBeNull()
	expect(
		screen.getByText("Get to level 3 in any concept to see players' numbers from matches you've watched.")
	).toBeInTheDocument()
})

test('stage three shows numbers for players the viewer has seen, and says who they haven’t', async () => {
	show(sheetStage3)
	expect(card()).toHaveTextContent('Niels Meiner')
	expect(within(card()).getByText('Passes completed').nextSibling).toHaveTextContent('74/110')
	expect(within(card()).getByText('+39%')).toBeInTheDocument()
	expect(card()).toHaveTextContent("From the 2 matches of theirs you've watched.")
	expect(screen.queryByText(/Get to level/)).toBeNull()

	await userEvent.click(within(pitch()).getByRole('button', { name: /Ousmane Ekekunle/ }))
	expect(within(card()).getByText("First time you've seen them")).toBeInTheDocument()
	expect(within(card()).queryByText('0')).toBeNull()
	expect(card()).toHaveTextContent("You haven't watched Bakewell Badgers yet, so there are no numbers for them.")
	expect(screen.queryByRole('button', { name: /Change it/ })).toBeNull()
})
