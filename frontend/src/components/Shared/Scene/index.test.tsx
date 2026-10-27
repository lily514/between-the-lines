import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FIXTURES } from '../../../scenes/fixtures/index.ts'
import { SPECS } from '../../../scenes/index.ts'
import type { SceneFixture, SceneSpec } from '../../../scenes/types.ts'
import Scene from './index.tsx'
import { appearFrames, beats, fill, percentOf, sceneView, travelFrames } from './index.support.ts'

const fixtureOf = (key: string): SceneFixture => {
	const fixture = FIXTURES[key]
	if (fixture === undefined) throw new Error(`no fixture for ${key}`)
	return fixture
}

const specOf = (key: string): SceneSpec => {
	const spec = SPECS[key]
	if (spec === undefined) throw new Error(`no spec for ${key}`)
	return spec
}

const show = (key: string, band: 'getting_there' | 'solid' | 'sharp' = 'getting_there') => {
	const { container } = render(
		<Scene spec={specOf(key)} fixture={fixtureOf(key)} band={band} name={fixtureOf(key).name} />
	)
	const svg = container.querySelector('svg')
	if (svg === null) throw new Error('no scene')
	return svg
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

test('the scene is decorative, drawn in the 5 : 4 crop with both teams and the ball', () => {
	const svg = show('restarts')
	expect(svg).toHaveAttribute('aria-hidden', 'true')
	const [, , width, height] = (svg.getAttribute('viewBox') ?? '').split(' ').map(Number)
	expect(width).toBeGreaterThanOrEqual(50)
	expect((width ?? 0) / (height ?? 1)).toBeCloseTo(1.25)
	expect(screen.getAllByTestId('scene-player-attacking')).toHaveLength(11)
	expect(screen.getAllByTestId('scene-player-defending')).toHaveLength(11)
	expect(screen.getByTestId('scene-ball')).toBeInTheDocument()
})

test('motion is CSS keyframes on a 5 s loop, written into the scene, and Pause holds every one of them', async () => {
	const svg = show('line_breaking_pass', 'solid')
	const css = svg.querySelector('style')?.textContent ?? ''
	expect(css).toMatch(/@keyframes scene-\w+-ball\{0%,/)
	expect(css).toMatch(/@keyframes scene-\w+-i\d+\{/)
	expect(screen.getByTestId('scene-ball').getAttribute('style')).toMatch(/scene-\w+-ball 5s/)
	expect(svg).toHaveClass('scene__svg--moving')
	expect(svg).not.toHaveClass('scene__svg--paused')

	const pause = screen.getByRole('button', { name: 'Pause motion in the Line-breaking passes scene' })
	expect(pause).toHaveAttribute('aria-pressed', 'false')
	await userEvent.click(pause)
	expect(svg).toHaveClass('scene__svg--paused')
	expect(screen.getByRole('button', { name: 'Play motion in the Line-breaking passes scene' })).toHaveAttribute(
		'aria-pressed',
		'true'
	)
})

test('with reduced motion there is no loop and no pause button, just a still frame', () => {
	reduceMotion(true)
	const svg = show('restarts')
	expect(svg.querySelector('style')).toBeNull()
	expect(svg).toHaveAttribute('data-still', 'start')
	expect(svg).not.toHaveClass('scene__svg--moving')
	expect(screen.queryByRole('button')).toBeNull()
	// The start frame: the ball where the play began, and nothing that appears later.
	expect(screen.getByTestId('scene-ball')).not.toHaveStyle({ transform: expect.anything() as string })
	expect(svg.querySelector('.scene__ring')).toBeNull()
})

test('Offside and Fouls and cards show the end frame when motion is reduced, so the call is visible', () => {
	reduceMotion(true)
	const svg = show('offside', 'solid')
	expect(svg).toHaveAttribute('data-still', 'end')
	expect(svg.querySelector('.scene__word')?.textContent).toBe('OFFSIDE')
	expect(screen.getByTestId('scene-ball').getAttribute('style')).toMatch(/translate\(/)
	expect(SPECS.fouls_and_cards?.still).toBe('end')
})

test('the layers draw what the handoff lists, with the numbers from the facts', () => {
	const texts = (key: string, band: 'getting_there' | 'solid' | 'sharp') =>
		[...show(key, band).querySelectorAll('text')].map(text => text.textContent)
	expect(texts('line_breaking_pass', 'getting_there').filter(t => /[A-Z]{3}/.test(t))).toEqual([])
	expect(texts('line_breaking_pass', 'solid')).toEqual(
		expect.arrayContaining(['DEFENCE', 'MIDFIELD', 'GAP 13 m', '1', 'BETWEEN THE LINES'])
	)
	expect(texts('line_breaking_pass', 'sharp')).toEqual(
		expect.arrayContaining(['1.6%', '2.4%', 'THREAT PER ZONE · xT'])
	)
	expect(texts('offside', 'solid')).toEqual(
		expect.arrayContaining(['SECOND-LAST DEFENDER', '2.3 m BEYOND', 'OFFSIDE'])
	)
	expect(texts('counter_press', 'solid')).toEqual(
		expect.arrayContaining(['0 s', '2 s', 'BACK IN 2.5 s', 'TWO PRESSERS'])
	)
	expect(texts('counter_press', 'sharp')).toEqual(
		expect.arrayContaining(['46.7 m FROM GOAL', 'SPACE BEHIND IF IT FAILS'])
	)
	expect(texts('restarts', 'solid')).toEqual(expect.arrayContaining(['LAST TOUCH', 'CORNER · RIPON WARDENS']))
	expect(texts('fouls_and_cards', 'solid')).toEqual(
		expect.arrayContaining(['FOUL', 'RIPON WARDENS GET A FREE KICK.'])
	)
})

test('beats spread the touches through the story, shortening long waits', () => {
	expect(beats([0, 27.5, 30.9])).toEqual([0.08, 0.415, 0.75])
	expect(beats([0, 1, 2])).toEqual([0.08, 0.415, 0.75])
	expect(beats([0])).toEqual([0.08])
	expect(percentOf(0)).toBe(6)
	expect(percentOf(1)).toBe(86)
})

test('templates fill from the facts and leave an unknown key visible', () => {
	expect(fill('GAP {gap_m} m', { gap_m: '13' })).toBe('GAP 13 m')
	expect(fill('{nope}', {})).toBe('{nope}')
})

test('keyframes appear on their beat and travel between stops', () => {
	expect(appearFrames('a', 0)).toBe('')
	expect(appearFrames('a', 0.5)).toBe('@keyframes a{0%,45.9%{opacity:0}46%,100%{opacity:1}}')
	expect(appearFrames('a', 0.25, 0.5)).toBe(
		'@keyframes a{0%,25.9%{opacity:0}26%,45.9%{opacity:1}46%,100%{opacity:0}}'
	)
	expect(
		travelFrames('b', [
			{ beat: 0, dx: 0, dy: 0 },
			{ beat: 0.5, dx: 3, dy: -4 }
		])
	).toBe(
		'@keyframes b{0%,6%{transform:translate(0px,0px)}46%{transform:translate(3px,-4px)}86%,100%{transform:translate(3px,-4px)}}'
	)
})

test('the view is at least 50 × 40, grows to fit the play, and stays on the pitch', () => {
	expect(sceneView([[50, 34]])).toEqual({ x: 9, y: 35, width: 50, height: 40 })
	expect(sceneView([[0, 34]]).y).toBe(68)
	const wide = sceneView([
		[20, 34],
		[90, 34]
	])
	expect(wide.height).toBeGreaterThan(70)
	expect(wide.width / wide.height).toBeCloseTo(1.25)
})

test('a zone’s value is drawn after the players, so the player standing in the zone never hides it', () => {
	const svg = show('line_breaking_pass', 'sharp')
	const players = svg.querySelector('.pitch__players')
	const values = [...svg.querySelectorAll('.scene__pill text')].filter(text => text.textContent.endsWith('%'))
	expect(values.map(text => text.textContent)).toEqual(['1.6%', '2.4%'])
	for (const value of values) expect(players?.compareDocumentPosition(value)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
})

test('a note along the bottom starts at the left, clear of the Pause motion button', () => {
	const note = [...show('line_breaking_pass', 'sharp').querySelectorAll('text')].find(
		text => text.textContent === 'THREAT PER ZONE · xT'
	)
	expect(note).toHaveAttribute('text-anchor', 'start')
})
