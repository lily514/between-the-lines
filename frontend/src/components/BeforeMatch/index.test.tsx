import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeMatchFirstLook, beforeMatchLevelUp } from '../../test-fixtures/index.ts'
import BeforeMatch from './index.tsx'
import { stepsOf, summaryOf, words } from './index.support.ts'

const show = (before = beforeMatchLevelUp, flow: 'first_look' | 'level_up' = 'level_up') => {
	const on = { onMap: vi.fn(), onDone: vi.fn() }
	render(<BeforeMatch before={before} flow={flow} {...on} />)
	return on
}

test('a Level-up is a step per concept that moved up, with its scene at the new level and how it got there', async () => {
	show()
	expect(screen.getByText('Before match 2')).toBeInTheDocument()
	expect(screen.getByText('1 of 2')).toBeInTheDocument()
	expect(screen.getByRole('heading', { level: 2, name: 'Count the lines' })).toHaveFocus()
	expect(screen.getByText('Possession · Line-breaking passes')).toBeInTheDocument()
	expect(screen.getByText('Now Solid').querySelector('.level-icon')?.getAttribute('data-band')).toBe('solid')
	expect(screen.getByText(/^15%/).closest('p')).toHaveTextContent(/15% → 53%.*Now Solid/)
	expect(screen.getByText('At Solid, you might get')).toBeInTheDocument()
	expect(screen.getByText(/Where should the pass go\?$/)).toBeInTheDocument()
	expect(screen.getByRole('button', { name: /Pause motion in the Line-breaking passes scene/ })).toBeInTheDocument()
	await userEvent.click(screen.getByRole('button', { name: 'Next' }))
	expect(screen.getByRole('heading', { level: 2, name: 'Ready for match 2.' })).toHaveFocus()
})

test('the last step lists every level with the moved ones marked new, the unlock note, the map and the way on', async () => {
	const { onMap, onDone } = show()
	await userEvent.click(screen.getByRole('button', { name: 'Skip' }))
	expect(
		screen.getByText('One thing moves up to Solid. Questions on those now use the real terms and shirt numbers.')
	).toBeInTheDocument()
	const rows = within(screen.getByRole('list', { name: 'Your levels' })).getAllByRole('listitem')
	expect(rows).toHaveLength(8)
	const line = rows.find(row => row.textContent.startsWith('Line-breaking passes'))
	expect(line).toHaveTextContent('Line-breaking passesNewSolid53%')
	expect(within(screen.getByRole('list', { name: 'Your levels' })).getAllByText('New')).toHaveLength(1)
	expect(screen.getByText('Unlocks after Tackles and turnovers and Restarts')).toBeInTheDocument()
	expect(screen.getByText(beforeMatchLevelUp.unlock_note ?? '')).toBeInTheDocument()
	await userEvent.click(screen.getByRole('button', { name: 'See your full map' }))
	expect(onMap).toHaveBeenCalledOnce()
	await userEvent.click(screen.getByRole('button', { name: 'On to Who’s playing' }))
	expect(onDone).toHaveBeenCalledOnce()
	expect(screen.queryByRole('button', { name: 'Skip' })).toBeNull()
})

test('a First look introduces each new concept at Getting there, with no level tag icon and no numbers', async () => {
	show(beforeMatchFirstLook, 'first_look')
	// The flow label, and the tag on the scene.
	expect(screen.getAllByText('First look')).toHaveLength(2)
	expect(screen.getByText('1 of 4')).toBeInTheDocument()
	expect(screen.getByText('Pressure · Tackles and turnovers')).toBeInTheDocument()
	expect(screen.getByText('Everyone starts at Getting there')).toBeInTheDocument()
	expect(screen.queryByText(/\d+%/)).toBeNull()
	expect(screen.getByText('You might get')).toBeInTheDocument()
	await userEvent.click(screen.getByRole('button', { name: 'Skip' }))
	expect(screen.getByRole('heading', { level: 2, name: 'That’s all three.' })).toHaveFocus()
	expect(within(screen.getByRole('list', { name: 'Your levels' })).getAllByText('New')).toHaveLength(3)
	expect(screen.queryByText(/New on Who’s playing/)).toBeNull()
})

test('the steps and summary come from the flow', () => {
	expect(stepsOf(beforeMatchFirstLook, 'first_look').map(step => [step.key, step.tag, step.before])).toEqual([
		['tackles', 'First look', null],
		['shots_and_goals', 'First look', null],
		['transitions', 'First look', null]
	])
	expect(stepsOf(beforeMatchLevelUp, 'level_up').map(step => [step.key, step.tag, step.band])).toEqual([
		['line_breaking_pass', 'Now Solid', 'solid']
	])
	const up = beforeMatchLevelUp.level_ups[0]
	if (up === undefined) throw new Error('fixture lacks a level-up')
	const sharp = {
		...beforeMatchLevelUp,
		match_number: 3,
		level_ups: [
			{ ...up, level: 'Sharp', band: 'sharp' as const },
			{ ...up, key: 'offside', level: 'Sharp', band: 'sharp' as const }
		]
	}
	expect(summaryOf(sharp, 'level_up')).toEqual({
		title: 'Ready for match 3.',
		body: 'Two things move up to Sharp. On those, you’ll get the analyst view.'
	})
	const mixed = { ...sharp, level_ups: [{ ...up, level: 'Sharp', band: 'sharp' as const }, up] }
	expect(summaryOf(mixed, 'level_up').body).toBe('Two things move up a level.')
	expect(words(3)).toBe('three')
	expect(words(12)).toBe('12')
})
