import { render, screen } from '@testing-library/react'
import MovingPitch from './MovingPitch.tsx'
import type { Track } from './MovingPitch.support.ts'

const track: Track = {
	players: [
		{ shirt: 7, home: true },
		{ shirt: 9, home: true },
		{ shirt: 4, home: false }
	],
	frames: [
		{
			period: 1,
			at: 10,
			positions: [
				[40, 30],
				[70, 50],
				[60, 30]
			],
			on_ball: 0
		},
		{
			period: 1,
			at: 14,
			positions: [
				[50, 30],
				[72, 50],
				[62, 30]
			],
			on_ball: 1
		}
	],
	ball: [
		{ period: 1, at: 10, point: [40, 30] },
		{ period: 1, at: 13, point: [72, 50] },
		{ period: 1, at: 14, point: [72, 50] }
	]
}

const reduceMotion = (matches: boolean) => {
	Object.defineProperty(window, 'matchMedia', {
		configurable: true,
		writable: true,
		value: vi.fn().mockReturnValue({ matches, addEventListener: vi.fn(), removeEventListener: vi.fn() })
	})
}

afterEach(() => {
	Reflect.deleteProperty(window, 'matchMedia')
})

const centre = (element: Element): [number, number] => [
	Number(element.getAttribute('cx')),
	Number(element.getAttribute('cy'))
]

test('the pitch is decorative and shows every tracked player, numbers on home discs', () => {
	render(<MovingPitch track={track} at={10} yours={null} />)

	expect(screen.getByTestId('moving-pitch')).toHaveAttribute('aria-hidden', 'true')
	expect(screen.getAllByTestId('player-home')).toHaveLength(2)
	expect(screen.getAllByTestId('player-away')).toHaveLength(1)
	expect(screen.getAllByTestId('player-home').map(p => p.textContent)).toEqual(['7', '9'])
	expect(screen.queryByTestId('pitch-yours')).not.toBeInTheDocument()
})

test("the viewer's team gets the dashed ring", () => {
	render(<MovingPitch track={track} at={10} yours="away" />)

	expect(screen.getAllByTestId('pitch-yours')).toHaveLength(1)
})

test('the players and the ball move with the clock, the viewer attacking up', () => {
	const { rerender } = render(<MovingPitch track={track} at={10} yours={null} />)
	const ballAt10 = centre(screen.getByTestId('moving-pitch-ball'))

	rerender(<MovingPitch track={track} at={13} yours={null} />)

	const ballAt13 = centre(screen.getByTestId('moving-pitch-ball'))
	// Picture x runs up the screen: further up the pitch is a smaller screen y.
	expect(ballAt13[1]).toBeLessThan(ballAt10[1])
	// The halo follows the player on the ball, eased three quarters of the way: 40 + 10 × 0.84375 up the pitch.
	expect(centre(screen.getByTestId('moving-pitch-halo'))).toEqual([38, 105 - 48.4375])
})

test('with reduced motion the players wait for the next keyframe', () => {
	reduceMotion(true)
	render(<MovingPitch track={track} at={13.9} yours={null} />)

	expect(centre(screen.getByTestId('moving-pitch-halo'))).toEqual([38, 65])
})

test('an empty track shows no pitch', () => {
	const { container } = render(<MovingPitch track={{ players: [], frames: [], ball: [] }} at={0} yours={null} />)

	expect(container).toBeEmptyDOMElement()
})
