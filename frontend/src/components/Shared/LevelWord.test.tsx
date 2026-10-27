import { render, screen } from '@testing-library/react'
import LevelWord from './LevelWord.tsx'
import { unlocksAfter } from './LevelWord.support.ts'

test('a level shows its word with the icon for its band', () => {
	const { container } = render(<LevelWord level="Solid" band="solid" />)
	expect(screen.getByText('Solid')).toBeInTheDocument()
	expect(container.querySelector('.level-icon')?.getAttribute('data-band')).toBe('solid')
})

test('a concept that waits on another reads as locked, with no icon', () => {
	const { container } = render(
		<LevelWord level="Getting there" band="getting_there" waitsFor={['Tackles and turnovers', 'Restarts']} />
	)
	expect(screen.getByText('Unlocks after Tackles and turnovers and Restarts')).toHaveClass('level-word--locked')
	expect(screen.queryByText('Getting there')).toBeNull()
	expect(container.querySelector('.level-icon')).toBeNull()
})

test('mastered shows the tick even if a prerequisite is listed', () => {
	const { container } = render(<LevelWord level="Mastered" band="sharp" mastered waitsFor={['Restarts']} />)
	expect(screen.getByText('Mastered')).toBeInTheDocument()
	expect(container.querySelector('.level-icon')?.getAttribute('data-band')).toBe('mastered')
})

test('the locked line names one prerequisite plainly and lists several', () => {
	expect(unlocksAfter(['Tackles and turnovers'])).toBe('Unlocks after Tackles and turnovers')
	expect(unlocksAfter(['A', 'B', 'C'])).toBe('Unlocks after A, B and C')
	expect(unlocksAfter([])).toBe('')
})
