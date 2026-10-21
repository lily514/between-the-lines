import { render } from '@testing-library/react'
import sprite from '../../assets/crests.svg?raw'
import Crest from './Crest.tsx'

// The league's clubs, by the codes the API sends.
const CODES = ['RIP', 'HEX', 'ALN', 'BAK', 'TRU', 'WEL', 'PEN', 'SHE', 'LUD', 'WHI']

test('the crest sprite is well-formed and has a crest for every club', () => {
	const parsed = new DOMParser().parseFromString(sprite, 'image/svg+xml')
	expect(parsed.querySelector('parsererror')).toBeNull()
	const ids = [...parsed.querySelectorAll('symbol')].map(symbol => symbol.id)
	expect(ids.sort()).toEqual(CODES.map(code => `crest-${code}`).sort())
})

test('a crest is hidden from screen readers, since the club name is always beside it', () => {
	const { container } = render(<Crest code="HEX" size={36} />)
	const svg = container.querySelector('svg')
	expect(svg).toHaveAttribute('aria-hidden', 'true')
	expect(svg?.querySelector('use')?.getAttribute('href')).toMatch(/#crest-HEX$/)
})
