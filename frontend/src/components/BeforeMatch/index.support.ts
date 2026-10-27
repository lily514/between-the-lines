import type { Band, BeforeMatch, LevelRow } from '../../api/client.ts'
import { CONCEPT_COPY, LEVEL_OF } from '../../scenes/copy.ts'
import { FIXTURES } from '../../scenes/fixtures/index.ts'
import type { BeforeFlow } from '../App.support.ts'

/** One concept's step in a flow: its scene at the level, the words for it, and how the viewer got there. */
export interface ConceptStep {
	key: string
	name: string
	strandName: string
	band: Band
	level: string
	/** Mastery before the last match; null on a First look, where everyone starts at the same place. */
	before: number | null
	after: number
	title: string
	body: string
	example: string
	tag: string
}

const WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']

export const words = (n: number) => WORDS[n] ?? String(n)

const stepOf = (
	row: { key: string; name: string; strand_name: string; band: Band; level: string },
	before: number | null,
	after: number,
	tag: string
): ConceptStep => {
	const copy = CONCEPT_COPY[row.key]?.[row.band]
	return {
		key: row.key,
		name: row.name,
		strandName: row.strand_name,
		band: row.band,
		level: row.level,
		before,
		after,
		title: copy?.title ?? row.name,
		body: copy?.body ?? `Questions about ${row.name.toLowerCase()} come at ${row.level}.`,
		example: FIXTURES[row.key]?.questions[LEVEL_OF[row.band]]?.text ?? copy?.example ?? '',
		tag
	}
}

/** The flow's concept steps: a First look at each new concept, or each concept whose level rose (one step, however far). */
export const stepsOf = (before: BeforeMatch, flow: BeforeFlow): ConceptStep[] =>
	flow === 'first_look'
		? before.first_looks.map(row => stepOf(row, null, row.mastery, 'First look'))
		: before.level_ups.map(up => stepOf(up, up.before, up.after, `Now ${up.level}`))

export const flowLabel = (before: BeforeMatch, flow: BeforeFlow) =>
	flow === 'first_look' ? 'First look' : `Before match ${String(before.match_number)}`

/** The last step's title and paragraph. */
export const summaryOf = (before: BeforeMatch, flow: BeforeFlow): { title: string; body: string } => {
	if (flow === 'first_look') {
		const n = before.first_looks.length
		return {
			title: n === 1 ? 'That’s the new one.' : `That’s all ${words(n)}.`,
			body: 'Everyone starts at Getting there. Your answers take each one to Solid, then Sharp.'
		}
	}
	const ups = before.level_ups
	const n = ups.length
	const things = n === 1 ? 'One thing moves' : `${capital(words(n))} things move`
	const levels = new Set(ups.map(up => up.level))
	const level = levels.size === 1 ? (ups[0]?.level ?? '') : null
	const body =
		level === 'Solid'
			? `${things} up to Solid. Questions on those now use the real terms and shirt numbers.`
			: level === 'Sharp' || level === 'Mastered'
				? `${things} up to ${level}. On those, you’ll get the analyst view.`
				: `${things} up a level.`
	return { title: `Ready for match ${String(before.match_number)}.`, body }
}

const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

/** The rows marked new on the level list: concepts just introduced, or whose level rose. */
export const isNew = (row: LevelRow, before: BeforeMatch, flow: BeforeFlow) =>
	flow === 'first_look' ? before.first_looks.some(look => look.key === row.key) : row.moved

/** The example card's label: plain on a First look, at the level reached on a Level-up. */
export const exampleLabel = (step: ConceptStep) =>
	step.before === null ? 'You might get' : `At ${step.level}, you might get`
