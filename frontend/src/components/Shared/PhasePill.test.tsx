import { render, screen } from '@testing-library/react'
import PhasePill from './PhasePill.tsx'
import { pillText } from './PhasePill.support.ts'

test('each phase of play has its own words', () => {
	expect(pillText('settled')).toBe('Settled possession')
	expect(pillText('transition')).toBe('Transition')
	expect(pillText('dead ball', 'corner')).toBe('Dead ball · corner')
	expect(pillText('half-time')).toBe('Half-time')
	expect(pillText('full time')).toBe('Full time')
	expect(pillText('your read')).toBe('Your read')
})

test('an unknown phase is shown as sent, without an icon', () => {
	const { container } = render(<PhasePill phase="extra time" />)
	expect(screen.getByText('extra time')).toBeInTheDocument()
	expect(container.querySelector('svg')).toBeNull()
})

test('a known phase has an icon beside its words', () => {
	const { container } = render(<PhasePill phase="dead ball" detail="goal kick" />)
	expect(screen.getByText('Dead ball · goal kick')).toBeInTheDocument()
	expect(container.querySelector('svg')).not.toBeNull()
})

test('a live question’s pill uses the action colour', () => {
	const { container } = render(<PhasePill phase="your read" />)
	expect(container.firstChild).toHaveClass('phase-pill--act')
})
