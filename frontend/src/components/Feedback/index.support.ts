import type { Feedback } from '../../api/client.ts'

/** How each measured fact is labelled on its tile, in the order the tiles appear. The value is always the pack's own
 * display text; only the label and unit are written here. */
const STAT_LABELS: Readonly<Record<string, { label: string; unit?: string }>> = {
	lines_broken: { label: 'Lines broken' },
	gap_m: { label: 'Gap', unit: 'm' },
	threat_added: { label: 'Chance added' },
	xt_before: { label: 'Chance before' },
	xt_after: { label: 'Chance after' },
	seconds_to_regain: { label: 'Won back in', unit: 's' },
	pressers: { label: 'Players pressing' },
	metres_from_goal: { label: 'From goal', unit: 'm' }
}

/** Facts that name a player or a part of the pitch. The explanation already says them, and they aren't measurements,
 * so they get no tile. */
const NOT_STATS = new Set(['receiver', 'receiver_zone', 'player'])

export interface Stat {
	key: string
	label: string
	value: string
	unit?: string
}

/** A tile for every measured outcome fact: known ones first in a fixed order, any others after with a label made
 * from their name, so a fact added to the pack later still shows. */
export const statTiles = (feedback: Feedback): Stat[] => {
	const names = Object.keys(feedback.outcome).filter(name => !NOT_STATS.has(name))
	const known = Object.keys(STAT_LABELS)
	const ordered = [...known.filter(name => names.includes(name)), ...names.filter(name => !known.includes(name))]
	return ordered.flatMap(name => {
		const fact = feedback.outcome[name]
		if (fact === undefined) {
			return []
		}
		const shown = STAT_LABELS[name] ?? { label: humanise(name) }
		return [{ key: name, value: fact.display, ...shown }]
	})
}

/** `seconds_to_regain` → "Seconds to regain". */
export const humanise = (name: string) => {
	const words = name.replaceAll('_', ' ')
	return words.charAt(0).toUpperCase() + words.slice(1)
}

/** "You picked A: Pass to #14 Niels Rosinga." and, after a wrong pick, which one it was. */
export const pickedLine = (feedback: Feedback) => {
	const label = (key: string | null) => feedback.options.find(o => o.key === key)?.label ?? ''
	const picked = `You picked ${feedback.chosen ?? ''}: ${label(feedback.chosen)}.`
	return feedback.correct ? picked : `${picked} It was ${feedback.correct_key}.`
}

/** Where the evidence came from, so every number can be traced: the match, the action, and who wrote the words. */
export const sourceLine = (feedback: Feedback) =>
	`Source · match ${String(feedback.match_seed)} · action ${String(feedback.action_id)} · worded by ${feedback.source}`

/** The asked concept's move, for its bar. */
export const askedConcept = (feedback: Feedback) => feedback.concepts.find(c => c.name === feedback.concept_name)
