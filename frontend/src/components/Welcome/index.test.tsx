import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { curriculum } from '../../test-fixtures/index.ts'
import Welcome from './index.tsx'
import { askedNow, summaryRows, welcomeSteps } from './index.support.ts'

const show = (props: Partial<Parameters<typeof Welcome>[0]> = {}) => {
	const handlers = { onStart: vi.fn(), onSeeAll: vi.fn() }
	render(<Welcome curriculum={curriculum} error={null} {...handlers} {...props} />)
	return handlers
}

const withoutChances = {
	...curriculum,
	concepts: curriculum.concepts.map(c => (c.strand === 'chances' ? { ...c, askable: false } : c))
}

test('the welcome opens on an intro to what the app is and how it works', async () => {
	const { onStart } = show()
	expect(
		screen.getByRole('heading', { level: 2, name: 'From ‘what just happened?’ to ‘I saw that coming.’' })
	).toHaveFocus()
	expect(screen.getByText(/adaptive learning tool for football fans at every level/)).toBeInTheDocument()
	const how = within(screen.getByRole('list', { name: 'How it works' })).getAllByRole('listitem')
	expect(how).toHaveLength(4)
	expect(how[1]).toHaveTextContent('Answer when play stops')
	expect(screen.queryByText(/of 5$/)).toBeNull()

	await userEvent.click(screen.getByRole('button', { name: 'Show me what I’ll learn' }))
	expect(screen.getByRole('heading', { level: 2, name: 'When play stops' })).toHaveFocus()
	await userEvent.click(screen.getByRole('button', { name: 'Back' }))
	expect(screen.getByRole('list', { name: 'How it works' })).toBeInTheDocument()

	await userEvent.click(screen.getByRole('button', { name: 'Skip the tour' }))
	expect(screen.getByRole('heading', { level: 2, name: 'You guess first. Then we show you.' })).toHaveFocus()
	expect(onStart).not.toHaveBeenCalled()
})

test('the welcome is a step per strand asked about now, each with its scene and what it covers', async () => {
	show()
	await userEvent.click(screen.getByRole('button', { name: 'Show me what I’ll learn' }))
	expect(screen.getByText('1 of 5')).toBeInTheDocument()
	expect(screen.getByRole('heading', { level: 2, name: 'When play stops' })).toHaveFocus()
	expect(screen.getByText('Game flow')).toBeInTheDocument()
	expect(
		screen.getByText('Restarts · Offside · Fouls and cards · Transitions and counterattacks')
	).toBeInTheDocument()
	expect(screen.getByRole('button', { name: /Pause motion in the Restarts scene/ })).toBeInTheDocument()
	expect(screen.getByText('You might get')).toBeInTheDocument()
	expect(screen.getByText(/What happens now\?$/)).toBeInTheDocument()

	await userEvent.click(screen.getByRole('button', { name: 'Next' }))
	expect(screen.getByRole('heading', { level: 2, name: 'Passes that slice through' })).toHaveFocus()
	expect(screen.getByText('2 of 5')).toBeInTheDocument()
	await userEvent.click(screen.getByRole('button', { name: 'Back' }))
	expect(screen.getByText('1 of 5')).toBeInTheDocument()
})

test('Chances has its own step now, with the Shots scene', async () => {
	show()
	await userEvent.click(screen.getByRole('button', { name: 'Show me what I’ll learn' }))
	for (let i = 0; i < 3; i += 1) await userEvent.click(screen.getByRole('button', { name: 'Next' }))
	expect(screen.getByRole('heading', { level: 2, name: 'Shots, and what comes of them' })).toBeInTheDocument()
	expect(screen.getByRole('button', { name: /Pause motion in the Shots and goals scene/ })).toBeInTheDocument()
	expect(screen.getByText('Shots and goals')).toBeInTheDocument()
})

test('Skip goes to the summary: what the questions cover, the levels, and Continue', async () => {
	const { onStart, onSeeAll } = show()
	await userEvent.click(screen.getByRole('button', { name: 'Show me what I’ll learn' }))
	await userEvent.click(screen.getByRole('button', { name: 'Skip' }))
	expect(screen.getByRole('heading', { level: 2, name: 'You guess first. Then we show you.' })).toHaveFocus()
	expect(screen.getByText('5 of 5')).toBeInTheDocument()
	expect(screen.queryByRole('button', { name: 'Skip' })).toBeNull()
	const rows = within(screen.getByRole('list', { name: 'What the questions cover' })).getAllByRole('listitem')
	expect(rows.map(row => row.textContent)).toEqual([
		'Game flowRestarts, Offside, Fouls and cards, Transitions and counterattacks',
		'PossessionLine-breaking passes',
		'PressureTackles and turnovers, Counter-pressing',
		'ChancesShots and goals'
	])
	const levels = within(screen.getByRole('list', { name: 'Levels' })).getAllByRole('listitem')
	expect(levels.map(level => level.textContent)).toEqual(['Getting there (you start here)', '→ Solid', '→ Sharp'])
	expect(screen.getByText('No sign-in. This browser keeps your place.')).toBeInTheDocument()
	await userEvent.click(screen.getByRole('button', { name: 'See all 20 concepts' }))
	expect(onSeeAll).toHaveBeenCalledOnce()
	await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
	expect(onStart).toHaveBeenCalledOnce()
})

test('the rows are by strand at eight concepts and one per concept below that', () => {
	expect(summaryRows(curriculum).map(row => row.name)).toEqual(['Game flow', 'Possession', 'Pressure', 'Chances'])
	const rows = summaryRows(withoutChances)
	expect(rows).toHaveLength(8)
	expect(rows.find(row => row.name === 'Chances')).toEqual({ name: 'Chances', detail: 'Coming later', later: true })
	expect(rows[0]).toEqual({ name: 'Restarts', detail: 'Game flow', later: false })
})

test('the steps run game flow first, then the other strands, skipping one with nothing asked about yet', () => {
	expect(welcomeSteps(curriculum).map(step => [step.key, step.scene])).toEqual([
		['game_flow', 'restarts'],
		['possession', 'line_breaking_pass'],
		['pressure', 'counter_press'],
		['chances', 'shots_and_goals']
	])
	expect(welcomeSteps(withoutChances).map(step => step.key)).toEqual(['game_flow', 'possession', 'pressure'])
	expect(askedNow(curriculum).map(group => group.concepts.length)).toEqual([4, 2, 1, 1])
})

test('a viewer sent back with an error lands on the summary, with the reason', () => {
	show({ error: 'The server could not be reached.' })
	expect(screen.getByRole('alert')).toHaveTextContent('The server could not be reached.')
	expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
})

test('it works before the curriculum has loaded: the intro, then the summary alone, with Continue', async () => {
	show({ curriculum: null })
	await userEvent.click(screen.getByRole('button', { name: 'Show me what I’ll learn' }))
	expect(screen.getByText('1 of 1')).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
	expect(screen.getByRole('button', { name: 'See all concepts' })).toBeInTheDocument()
	expect(screen.queryByRole('list', { name: 'What the questions cover' })).toBeNull()
})
