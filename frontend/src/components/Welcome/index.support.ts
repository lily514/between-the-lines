import type { ConceptMap, MapConcept } from '../../api/client.ts'

/** A strand with the concepts asked about now in it. */
export interface StrandGroup {
	key: string
	name: string
	concepts: MapConcept[]
}

/** The strands with what is asked about now in each, those with most first; a strand with none comes last. */
export const askedNow = (map: ConceptMap): StrandGroup[] =>
	map.strands
		.map(strand => ({
			key: strand.key,
			name: strand.name,
			concepts: map.concepts.filter(concept => concept.askable && concept.strand === strand.key)
		}))
		.sort((a, b) => b.concepts.length - a.concepts.length)
