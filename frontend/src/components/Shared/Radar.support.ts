import type { Report } from '../../api/client.ts'

type Strand = Report['strands'][number]

/** The radar's axes, clockwise from the top. A strand the API doesn't send is left out. */
export const AXIS_ORDER = ['possession', 'pressure', 'chances', 'game_flow']
export const RADIUS = 40
export const RINGS = [0.25, 0.5, 0.75, 1]

export interface Axis {
	strand: Strand
	/** Unit direction of the axis: up is (0, -1). */
	dx: number
	dy: number
}

export const axes = (strands: Strand[]): Axis[] => {
	const ordered = AXIS_ORDER.flatMap(key => strands.filter(strand => strand.key === key))
	return ordered.map((strand, i) => {
		const angle = (2 * Math.PI * i) / ordered.length - Math.PI / 2
		return { strand, dx: round(Math.cos(angle)), dy: round(Math.sin(angle)) }
	})
}

/** A polygon through the axes that have a value; an empty strand is skipped, so the shape closes across it. */
export const shape = (list: Axis[], value: (strand: Strand) => number | null): string =>
	list
		.flatMap(axis => {
			const v = value(axis.strand)
			return v === null ? [] : [`${String(round(axis.dx * RADIUS * v))},${String(round(axis.dy * RADIUS * v))}`]
		})
		.join(' ')

const round = (n: number) => Math.round(n * 1000) / 1000
