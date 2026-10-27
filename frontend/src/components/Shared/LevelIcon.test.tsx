import { render } from '@testing-library/react'
import LevelIcon from './LevelIcon.tsx'

const draw = (props: Parameters<typeof LevelIcon>[0]) => {
	const { container } = render(<LevelIcon {...props} />)
	const svg = container.querySelector('svg')
	if (svg === null) throw new Error('no icon')
	return svg
}

test('each band has its own fill: a quarter, a half, or the whole disc', () => {
	expect(draw({ band: 'getting_there' }).querySelector('path')?.getAttribute('d')).toMatch(/^M6 6 V1.2/)
	expect(draw({ band: 'solid' }).querySelector('path')?.getAttribute('d')).toMatch(/^M6 1.2 A/)
	const sharp = draw({ band: 'sharp' })
	expect(sharp.querySelector('.level-icon__ring')).toBeNull()
	expect(sharp.querySelector('circle')?.getAttribute('r')).toBe('5.4')
})

test('mastered is a full disc with a tick, whatever the band', () => {
	const icon = draw({ band: 'sharp', mastered: true })
	expect(icon.dataset.band).toBe('mastered')
	expect(icon.querySelector('.level-icon__tick')).not.toBeNull()
	expect(draw({ band: 'solid' }).querySelector('.level-icon__tick')).toBeNull()
})

test('the icon is decorative: the level word beside it carries the meaning', () => {
	expect(draw({ band: 'solid' })).toHaveAttribute('aria-hidden', 'true')
})
