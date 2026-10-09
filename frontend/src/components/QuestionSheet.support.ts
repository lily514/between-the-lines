import type { Question } from '../api/client.ts'
import type { PitchOption } from './Pitch.support.ts'

export const isLive = (question: Question) => question.delivered.delivery === 'live'

/** The pill: "Your read" for a live question, otherwise where play is now ("Dead ball · free kick", "Half-time"). */
export const sheetPill = (question: Question): { phase: string; detail: string | null } =>
	isLive(question)
		? { phase: 'your read', detail: null }
		: { phase: question.delivered.phase, detail: question.delivered.restart }

/** The clock now, and for a live question the score too. A review question's score is from when the play happened,
 * which may be out of date by now, so it isn't shown. */
export const clockLine = (question: Question): string => {
	const score = question.context.score?.display
	return isLive(question) && score !== undefined ? `${question.delivered.clock} · ${score}` : question.delivered.clock
}

/** When a review question's play happened, unless the worded question already says so ("Back at 05:12: …"). */
export const earlierAt = (question: Question): string | undefined =>
	isLive(question) || question.text.includes(question.occurred.clock) ? undefined : question.occurred.clock

/** Where each option's pass would go, for the pitch. Options that aren't passes have no target. */
export const pitchOptions = (question: Question): PitchOption[] =>
	question.options.flatMap(o => (o.target_at === null ? [] : [{ key: o.key, at: o.target_at }]))

/** A predict question never shows the play's path, since the path is the answer. */
export const shownPath = (question: Question) => (question.form === 'predict' ? [] : question.picture.path)

export const pitchLabel = (question: Question) =>
	isLive(question) ? `Freeze-frame at ${question.delivered.clock}` : `Replay of ${question.occurred.clock}`

/** The option chosen with keys 1, 2 and 3. */
export const keyedOption = (question: Question, key: string): string | undefined => {
	const index = Number(key) - 1
	return Number.isInteger(index) && index >= 0 ? question.options[index]?.key : undefined
}
