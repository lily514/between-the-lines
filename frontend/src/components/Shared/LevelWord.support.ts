/** The locked state's line: "Unlocks after Tackles and turnovers and Restarts". Names come from the API. */
export const unlocksAfter = (waitsFor: readonly string[]): string => {
	const last = waitsFor.at(-1)
	if (last === undefined) return ''
	const rest = waitsFor.slice(0, -1)
	return `Unlocks after ${rest.length === 0 ? last : `${rest.join(', ')} and ${last}`}`
}
