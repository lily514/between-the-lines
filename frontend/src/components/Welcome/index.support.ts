import type { ConceptMap, MapConcept } from '../../api/client.ts'
import { SCENE_FOR_STRAND, WELCOME_COPY, type StepCopy } from '../../scenes/copy.ts'
import { FIXTURES } from '../../scenes/fixtures/index.ts'

/** A strand with the concepts asked about now in it. */
export interface StrandGroup {
	key: string
	name: string
	concepts: MapConcept[]
}

/** A step of the welcome: one strand with something asked about now, its scene and its words. */
export interface WelcomeStep extends StrandGroup {
	/** The concept whose scene stands for the strand. */
	scene: string
	copy: StepCopy
	/** A question the viewer might really get, from the scene's fixture, worded as the Tutor would at Getting there. */
	example: string
}

/** Rows are listed by strand once there are this many concepts asked about now; fewer are listed one by one. */
export const GROUP_FROM = 8

/** The order the welcome tells the strands in: the basics of the game first; any other strand after, as the map has it. */
export const STRAND_ORDER = ['game_flow', 'possession', 'pressure', 'chances']

const rank = (key: string) => {
	const place = STRAND_ORDER.indexOf(key)
	return place === -1 ? STRAND_ORDER.length : place
}

/** The strands in the welcome's order, each with what is asked about now; a strand may have none. */
export const byStrand = (map: ConceptMap): StrandGroup[] =>
	[...map.strands]
		.sort((a, b) => rank(a.key) - rank(b.key))
		.map(strand => ({
			key: strand.key,
			name: strand.name,
			concepts: map.concepts.filter(concept => concept.askable && concept.strand === strand.key)
		}))

/** The strands with what is asked about now in each, those with most first; a strand with none comes last. */
export const askedNow = (map: ConceptMap): StrandGroup[] =>
	[...byStrand(map)].sort((a, b) => b.concepts.length - a.concepts.length)

/** One step per strand with a concept asked about now, in the map's order. */
export const welcomeSteps = (map: ConceptMap): WelcomeStep[] =>
	byStrand(map)
		.filter(group => group.concepts.length > 0)
		.map(group => {
			const preferred = SCENE_FOR_STRAND[group.key]
			const scene =
				group.concepts.find(concept => concept.key === preferred)?.key ?? group.concepts[0]?.key ?? group.key
			const copy = WELCOME_COPY[group.key] ?? {
				title: group.name,
				body: group.concepts.map(concept => concept.objective).join(' '),
				example: ''
			}
			return { ...group, scene, copy, example: FIXTURES[scene]?.questions['1']?.text ?? copy.example }
		})

export interface SummaryRow {
	name: string
	/** The concepts in a strand, or a concept's strand; "Coming later" for a strand with none. */
	detail: string
	later: boolean
}

/** The summary's rows: by strand at GROUP_FROM or more concepts asked about now, else one per concept. */
export const summaryRows = (map: ConceptMap): SummaryRow[] => {
	const groups = byStrand(map)
	const asked = groups.reduce((total, group) => total + group.concepts.length, 0)
	if (asked >= GROUP_FROM) {
		return groups.map(group => ({
			name: group.name,
			detail:
				group.concepts.length === 0 ? 'Coming later' : group.concepts.map(concept => concept.name).join(', '),
			later: group.concepts.length === 0
		}))
	}
	return groups.flatMap((group): SummaryRow[] =>
		group.concepts.length === 0
			? [{ name: group.name, detail: 'Coming later', later: true }]
			: group.concepts.map(concept => ({ name: concept.name, detail: group.name, later: false }))
	)
}
