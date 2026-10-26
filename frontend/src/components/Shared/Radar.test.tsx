import { reportFullTime } from '../../test-fixtures/index.ts'
import { axes, RADIUS, shape } from './Radar.support.ts'

test('the axes run clockwise from Possession at the top', () => {
	const list = axes(reportFullTime.strands)
	expect(list.map(axis => axis.strand.name)).toEqual(['Possession', 'Pressure', 'Chances', 'Game flow'])
	expect(list.map(axis => [axis.dx, axis.dy])).toEqual([
		[0, -1],
		[1, 0],
		[0, 1],
		[-1, 0]
	])
})

test('a strand with no value has no point, so the shape closes across it and never shows a zero', () => {
	const list = axes(reportFullTime.strands)
	const points = shape(list, strand => strand.now).split(' ')
	expect(points).toHaveLength(3)
	expect(points[0]).toBe(`0,${String(-Math.round(RADIUS * 0.15 * 1000) / 1000)}`)
})
