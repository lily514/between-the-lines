import { render, screen } from '@testing-library/react'
import ProgressBar from './ProgressBar.tsx'
import { barParts, percent } from './ProgressBar.support.ts'

test('a gain shows the part already known and what this answer added', () => {
	expect(barParts(0.51, 0.76)).toEqual({ kept: 51, gained: 25, lost: 0 })
})

test('a fall shows the stretch lost rather than hiding it', () => {
	const parts = barParts(0.43, 0.24)
	expect(parts.kept).toBeCloseTo(24)
	expect(parts.gained).toBe(0)
	expect(parts.lost).toBeCloseTo(19)
})

test('shares are rounded to whole percentages as the update sentence words them', () => {
	expect(percent(0.2375)).toBe(24)
	expect(percent(0.95)).toBe(95)
})

test('the ticks sit at the unlock and mastery thresholds', () => {
	const { container } = render(
		<ProgressBar name="Counter-pressing" before={0.2} after={0.5} unlock={0.8} mastery={0.95} />
	)
	expect(container.querySelector('.progress-bar__tick--unlock')).toHaveStyle({ left: '80%' })
	expect(container.querySelector('.progress-bar__tick--mastery')).toHaveStyle({ left: '95%' })
	expect(container.querySelector('.progress-bar__gained')).toHaveStyle({ width: '30%' })
	expect(container.querySelector('.progress-bar__lost')).toBeNull()
	expect(screen.getByRole('meter', { name: 'Counter-pressing' })).toHaveAttribute('aria-valuenow', '50')
})
