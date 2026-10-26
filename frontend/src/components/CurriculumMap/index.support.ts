import type { ConceptMap, MapConcept } from '../../api/client.ts'

/** The map's pitch, in its own units: one column per strand, one band per tier, the deepest tier at the top. */
export const MAP_WIDTH = 68
export const BAND = 40
/** Room at the top of each band for the tier's name, and under the last band for its names. */
export const BAND_HEAD = 4.5
export const FOOT = 4
const LABEL_CHARS = 10
const LABEL_LINES = 3

export interface PlacedConcept {
	concept: MapConcept
	x: number
	y: number
	/** The name, broken into short lines for under the node. */
	lines: string[]
	state: 'mastered' | 'asked' | 'later'
}

/** Where each concept sits: in its strand's column and tier's band, stacked evenly when a cell holds more than one. */
export const place = (map: ConceptMap): PlacedConcept[] => {
	const column = MAP_WIDTH / map.strands.length
	const tiers = map.tiers.length
	return map.concepts.map(concept => {
		const cell = map.concepts.filter(other => other.strand === concept.strand && other.tier === concept.tier)
		const index = cell.indexOf(concept)
		const strand = map.strands.findIndex(s => s.key === concept.strand)
		const top = (tiers - 1 - concept.tier) * BAND
		return {
			concept,
			x: column * (strand + 0.5),
			y: top + BAND_HEAD + ((BAND - BAND_HEAD) / cell.length) * index + 3.6,
			lines: labelLines(concept.name),
			state: stateOf(concept, map.thresholds.mastery)
		}
	})
}

/** Mastered, asked about now, or coming later: the three ways a node is drawn. */
export const stateOf = (concept: MapConcept, mastery: number): PlacedConcept['state'] => {
	if (!concept.askable) return 'later'
	return concept.mastery !== null && concept.mastery >= mastery ? 'mastered' : 'asked'
}

/** A name in lines of about ten characters, at most three, dropping a bracketed short form such as "(xT)". */
export const labelLines = (name: string): string[] => {
	// A long hyphenated word, such as "Counter-pressing", may break after its hyphen.
	const words = name
		.replace(/\s*\([^)]*\)/g, '')
		.split(' ')
		.flatMap(word => (word.length > LABEL_CHARS ? word.split(/(?<=-)/) : [word]))
	const lines: string[] = []
	for (const word of words) {
		const last = lines.at(-1)
		const joined = last?.endsWith('-') ? `${last}${word}` : `${last ?? ''} ${word}`
		if (last !== undefined && joined.length <= LABEL_CHARS) {
			lines[lines.length - 1] = joined
		} else {
			lines.push(word)
		}
	}
	return lines.length <= LABEL_LINES
		? lines
		: [...lines.slice(0, LABEL_LINES - 1), `${lines[LABEL_LINES - 1] ?? ''}…`]
}

/** Every concept a concept builds on, nearest first, without repeats. */
export const buildsOn = (map: ConceptMap, key: string): MapConcept[] => {
	const found: MapConcept[] = []
	const visit = (from: string) => {
		const concept = map.concepts.find(c => c.key === from)
		for (const before of concept?.prerequisites ?? []) {
			const prerequisite = map.concepts.find(c => c.key === before)
			if (prerequisite !== undefined && !found.includes(prerequisite)) {
				found.push(prerequisite)
				visit(before)
			}
		}
	}
	visit(key)
	return found
}

/** The concept the map opens on: the asked-about one the viewer is least sure of, so the next step shows first. */
export const startingConcept = (map: ConceptMap): MapConcept | null =>
	map.concepts
		.filter(concept => concept.askable)
		.reduce<MapConcept | null>(
			(best, concept) => (best === null || (concept.mastery ?? 0) < (best.mastery ?? 0) ? concept : best),
			null
		)
