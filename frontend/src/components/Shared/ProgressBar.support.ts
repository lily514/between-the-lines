/** A share from the learner model as a whole percentage, the way the update sentence words it. */
export const percent = (share: number) => Math.round(share * 100)

/** How the bar is split: the part known before and still known, then what was gained or lost this time. */
export interface BarParts {
	kept: number
	gained: number
	lost: number
}

/** Percentages of the bar's width. A drop is shown as the stretch lost, outlined, so the bar never hides a fall. */
export const barParts = (before: number, after: number): BarParts => {
	const from = clampPercent(before)
	const to = clampPercent(after)
	return { kept: Math.min(from, to), gained: Math.max(0, to - from), lost: Math.max(0, from - to) }
}

/** What a screen reader hears for the bar, e.g. "43% to 24%. Unlocks the next concept at 80%, mastered at 95%." */
export const barText = (before: number, after: number, unlock: number, mastery: number) =>
	`${String(percent(before))}% to ${String(percent(after))}%. ` +
	`Unlocks the next concept at ${String(percent(unlock))}%, mastered at ${String(percent(mastery))}%.`

const clampPercent = (share: number) => Math.min(100, Math.max(0, share * 100))
