import { layerItems, sceneData, textsOf } from '../components/Shared/Scene/index.support.ts'
import { FIXTURES } from './fixtures/index.ts'
import { SPECS } from './index.ts'
import { crossing, defendingLines } from './helpers.ts'
import type { SceneFixture } from './types.ts'

const BANDS = ['getting_there', 'solid', 'sharp'] as const
/** The concepts with a scene so far; T14 adds the three new ones and makes this every fixture. */
const DRAWN = ['restarts', 'offside', 'fouls_and_cards', 'line_breaking_pass', 'counter_press']

const fixtureOf = (key: string): SceneFixture => {
	const fixture = FIXTURES[key]
	if (fixture === undefined) throw new Error(`no fixture for ${key}`)
	return fixture
}

test('every drawn concept has a spec and a fixture, and the fixtures cover the active concepts', () => {
	expect(Object.keys(SPECS).sort()).toEqual([...DRAWN].sort())
	for (const key of DRAWN) expect(FIXTURES).toHaveProperty(key)
	expect(Object.keys(FIXTURES)).toHaveLength(8)
	for (const [key, fixture] of Object.entries(FIXTURES)) expect(fixture.concept).toBe(key)
})

test.each(DRAWN)('%s draws three layers whose every label is filled from the facts', key => {
	const spec = SPECS[key]
	if (spec === undefined) throw new Error('no spec')
	const scene = sceneData(fixtureOf(key))
	for (const band of BANDS) {
		const items = layerItems(spec, band, scene)
		expect(items.length).toBeGreaterThan(0)
		for (const text of textsOf(items)) {
			expect(text).not.toMatch(/[{}]/)
			expect(text.length).toBeLessThanOrEqual(40)
		}
		for (const item of items) {
			if ('beat' in item) expect(item.beat).toBeGreaterThanOrEqual(0)
			if ('until' in item) expect(item.until).toBeLessThanOrEqual(1)
		}
	}
})

test('Getting there has no numbers on the pitch', () => {
	for (const key of DRAWN) {
		const spec = SPECS[key]
		if (spec === undefined) throw new Error('no spec')
		const texts = textsOf(layerItems(spec, 'getting_there', sceneData(fixtureOf(key))))
		expect(texts.filter(text => /\d/.test(text))).toEqual([])
	}
})

test('Solid names the lines and shows one number; Sharp shows the analyst values', () => {
	const scene = sceneData(fixtureOf('line_breaking_pass'))
	const spec = SPECS.line_breaking_pass
	if (spec === undefined) throw new Error('no spec')
	expect(textsOf(layerItems(spec, 'solid', scene))).toEqual([
		'DEFENCE',
		'MIDFIELD',
		'GAP 13 m',
		'1',
		'BETWEEN THE LINES'
	])
	expect(textsOf(layerItems(spec, 'sharp', scene))).toContain('1.6%')
	expect(textsOf(layerItems(spec, 'sharp', scene))).toContain('2.4%')
})

test('the defending lines are read off the key frame, nearest their goal first', () => {
	const lines = defendingLines(sceneData(fixtureOf('line_breaking_pass')))
	expect(lines).toHaveLength(3)
	expect(lines[0]).toBeGreaterThan(lines[1] ?? 0)
	expect(lines[0]).toBeCloseTo(91.5, 0)
	expect(crossing([72.8, 43.3], [89.1, 54], lines[1] ?? 0)?.[0]).toBe(lines[1])
	expect(crossing([72.8, 43.3], [89.1, 54], lines[0] ?? 0)).toBeNull()
})
