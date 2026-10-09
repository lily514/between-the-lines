export interface Choice {
	key: string
	label: string
}

/** How a tile looks: before answering it is idle or selected; after the reveal it is the answer, the wrong pick, or
 * neither. */
export type TileState = 'idle' | 'selected' | 'correct' | 'incorrect' | 'missed'

/** After the reveal: which option was right, and which one the viewer picked. */
export interface Outcome {
	correct: string
	chosen: string
}

/** Labels up to this long fit two lines of a third-width tile on a 390 px phone. */
export const SHORT_LABEL = 18

/** Three tiles side by side when every label is short ("One", "Back to #12"), otherwise one full-width row each. */
export const layoutFor = (choices: readonly Choice[]): 'columns' | 'rows' =>
	choices.every(c => c.label.length <= SHORT_LABEL) ? 'columns' : 'rows'

export const tileState = (key: string, selected: string | null, outcome?: Outcome): TileState => {
	if (outcome === undefined) {
		return key === selected ? 'selected' : 'idle'
	}
	if (key === outcome.correct) {
		return 'correct'
	}
	return key === outcome.chosen ? 'incorrect' : 'missed'
}

/** Arrow keys move through the options and wrap around, as a radio group does. */
export const stepFrom = (index: number, key: string, count: number): number | undefined => {
	if (key === 'ArrowRight' || key === 'ArrowDown') {
		return (index + 1) % count
	}
	if (key === 'ArrowLeft' || key === 'ArrowUp') {
		return (index - 1 + count) % count
	}
	if (key === 'Home') {
		return 0
	}
	if (key === 'End') {
		return count - 1
	}
	return undefined
}
