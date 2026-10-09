import { render, screen } from '@testing-library/react'
import { identifyQuestion as identify, predictFeedback, predictQuestion as predict } from '../test-fixtures/index.ts'
import Pitch from './Pitch.tsx'

const options = predict.options.flatMap(o => (o.target_at === null ? [] : [{ key: o.key, at: o.target_at }]))

test('home players are filled discs and away players are rings', () => {
	render(<Pitch picture={predict.picture} label="Freeze-frame" />)
	const home = predict.picture.markers.filter(m => m.home).length
	const away = predict.picture.markers.length - home
	expect(screen.getAllByTestId('player-home')).toHaveLength(home)
	expect(screen.getAllByTestId('player-away')).toHaveLength(away)
	for (const disc of screen.getAllByTestId('player-home')) {
		expect(disc.querySelector('text')).not.toBeNull()
	}
	for (const ring of screen.getAllByTestId('player-away')) {
		expect(ring.querySelector('text')).toBeNull()
	}
})

test('a predict question shows the options and no path', () => {
	render(
		<Pitch
			picture={predict.picture}
			options={options}
			path={predict.picture.path}
			crop="moment"
			label="Freeze-frame"
		/>
	)
	expect(screen.queryByTestId('pitch-path')).toBeNull()
	expect(screen.getByTestId('pitch-options').querySelectorAll('path')).toHaveLength(options.length)
	expect(screen.getByRole('img').getAttribute('viewBox')).not.toBe('-3 -3 74 111')
})

test('a review question shows the play’s path', () => {
	render(<Pitch picture={identify.picture} path={identify.picture.path} label="Earlier" />)
	expect(screen.getByTestId('pitch-path')).not.toHaveClass('pitch__path--reveal')
})

test('the reveal traces the real path', () => {
	render(
		<Pitch
			picture={predictFeedback.picture}
			path={predictFeedback.reveal_path}
			reveal
			crop="moment"
			label="The reveal"
		/>
	)
	const path = screen.getByTestId('pitch-path')
	expect(path).toHaveClass('pitch__path--reveal')
	expect(path.getAttribute('pathLength')).toBe('1')
})

test('players away from the moment are dimmed only when there is a moment', () => {
	const { container, unmount } = render(<Pitch picture={predict.picture} label="Pitch" />)
	expect(container.querySelectorAll('.pitch__player--dim')).toHaveLength(0)
	unmount()
	const focused = render(<Pitch picture={predict.picture} options={options} label="Pitch" />)
	const dimmed = focused.container.querySelectorAll('.pitch__player--dim').length
	expect(dimmed).toBe(predict.picture.markers.length - 1 - options.length)
})

test('the pitch has a label for screen readers', () => {
	render(<Pitch picture={predict.picture} options={options} label="Freeze-frame at 05:12" />)
	expect(
		screen.getByRole('img', { name: /Freeze-frame at 05:12\. The team on the ball is attacking upwards\./ })
	).toBeInTheDocument()
})

test('home discs are drawn over away rings, so shirt numbers stay readable', () => {
	render(<Pitch picture={predict.picture} options={options} label="Freeze-frame" />)
	for (const dimmed of [true, false]) {
		const shapes = screen
			.getAllByTestId(/^player-/)
			.filter(p => p.classList.contains('pitch__player--dim') === dimmed)
			.map(p => p.dataset.testid)
		const firstHome = shapes.indexOf('player-home')
		const lastAway = shapes.lastIndexOf('player-away')
		if (firstHome !== -1 && lastAway !== -1) expect(lastAway).toBeLessThan(firstHome)
	}
})

test('the path and the option lines start at the drawn ball, not on the player', () => {
	const { container } = render(
		<Pitch picture={identify.picture} path={identify.picture.path} options={options} label="Freeze-frame" />
	)
	const ball = container.querySelector('.pitch__ball')
	const start = (d: string | null) =>
		d
			?.match(/^M(\S+) (\S+)/)
			?.slice(1)
			.map(Number)
	const at = [Number(ball?.getAttribute('cx')), Number(ball?.getAttribute('cy'))]
	const path = start(screen.getByTestId('pitch-path').getAttribute('d'))
	expect(path?.[0]).toBeCloseTo(at[0] ?? NaN, 1)
	expect(path?.[1]).toBeCloseTo(at[1] ?? NaN, 1)
	for (const line of container.querySelectorAll('.pitch__option-line')) {
		const from = start(line.getAttribute('d'))
		expect(from?.[0]).toBeCloseTo(at[0] ?? NaN, 1)
	}
})
