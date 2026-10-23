import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { conceptMap, curriculum } from '../../test-fixtures/index.ts'
import CurriculumMap from './index.tsx'
import { BAND, buildsOn, labelLines, MAP_WIDTH, place, stateOf } from './index.support.ts'

test('every concept sits in its strand’s column and its tier’s band, deepest at the top', () => {
	const placed = place(conceptMap)
	expect(placed).toHaveLength(20)
	for (const node of placed) {
		const strand = conceptMap.strands.findIndex(s => s.key === node.concept.strand)
		const column = MAP_WIDTH / conceptMap.strands.length
		expect(node.x).toBeCloseTo(column * (strand + 0.5))
		const top = (conceptMap.tiers.length - 1 - node.concept.tier) * BAND
		expect(node.y).toBeGreaterThan(top)
		expect(node.y).toBeLessThan(top + BAND)
	}
	const restarts = placed.find(node => node.concept.name === 'Restarts')
	const offside = placed.find(node => node.concept.name === 'Offside')
	expect(restarts?.x).toBe(offside?.x)
	expect(restarts?.y).not.toBe(offside?.y)
})

test('names break into short lines, after a hyphen if need be, without a bracketed short form', () => {
	expect(labelLines('Counter-pressing')).toEqual(['Counter-', 'pressing'])
	expect(labelLines('Fouls and cards')).toEqual(['Fouls and', 'cards'])
	expect(labelLines('Expected goals (xG)')).toEqual(['Expected', 'goals'])
	expect(labelLines('Expected threat (xT) and possession value')).toHaveLength(3)
})

test('a concept builds on its prerequisites and theirs, nearest first', () => {
	const line = conceptMap.concepts.find(c => c.name === 'Line-breaking passes')
	expect(buildsOn(conceptMap, line?.key ?? '').map(c => c.name)).toEqual([
		'Passing and pass difficulty',
		'Possession'
	])
})

test('nodes are mastered, asked now, or coming later', () => {
	const later = conceptMap.concepts.find(c => !c.askable)
	const asked = conceptMap.concepts.find(c => c.askable)
	if (later === undefined || asked === undefined) throw new Error('fixture lacks concepts')
	expect(stateOf(later, 0.95)).toBe('later')
	expect(stateOf({ ...asked, mastery: 0.5 }, 0.95)).toBe('asked')
	expect(stateOf({ ...asked, mastery: 0.96 }, 0.95)).toBe('mastered')
})

test('the map opens on a concept asked now, and choosing another by keyboard fills the card', async () => {
	render(<CurriculumMap map={conceptMap} error={null} onBack={vi.fn()} />)
	expect(screen.getByRole('heading', { name: 'Your pitch' })).toHaveFocus()
	expect(screen.getByText('0 of 20 mastered')).toBeInTheDocument()
	const offside = screen.getByRole('button', { name: /^Offside: / })
	await userEvent.click(offside)
	expect(offside).toHaveAttribute('aria-pressed', 'true')
	expect(screen.getByText('Game flow · Tier 0, Newcomer')).toBeInTheDocument()
	await userEvent.keyboard('{Tab}')
	expect(screen.getByRole('button', { name: /^Fouls and cards: / })).toHaveAttribute('aria-pressed', 'true')
})

test('coming-later concepts say so, and the list gives the same choices as plain buttons', async () => {
	render(<CurriculumMap map={curriculum} error={null} onBack={vi.fn()} />)
	expect(screen.getByRole('button', { name: 'Game state: Coming later' })).toBeInTheDocument()
	await userEvent.click(screen.getByText('All 20 concepts as a list'))
	await userEvent.click(screen.getByRole('button', { name: 'Game state' }))
	expect(screen.getByText('Game flow · Tier 2, Engaged fan')).toBeInTheDocument()
})

test('Back and Esc close the map', async () => {
	const onBack = vi.fn()
	render(<CurriculumMap map={conceptMap} error={null} onBack={onBack} />)
	await userEvent.click(screen.getByRole('button', { name: 'Close the map and go back to where you were' }))
	await userEvent.keyboard('{Escape}')
	expect(onBack).toHaveBeenCalledTimes(2)
})
