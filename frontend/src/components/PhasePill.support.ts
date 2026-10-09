/** The phases of play the API sends (the engine's `PhaseOfPlay` values), plus the pill shown for a live question. */
export type PillKind = 'settled' | 'transition' | 'dead ball' | 'half-time' | 'full time' | 'your read'

const WORDS: Record<PillKind, string> = {
	settled: 'Settled possession',
	transition: 'Transition',
	'dead ball': 'Dead ball',
	'half-time': 'Half-time',
	'full time': 'Full time',
	'your read': 'Your read'
}

export const pillKind = (phase: string): PillKind | undefined => (phase in WORDS ? (phase as PillKind) : undefined)

/** The pill's words: "Dead ball · free kick" when the restart is known. An unknown phase is shown as sent. */
export const pillText = (phase: string, detail?: string | null): string => {
	const kind = pillKind(phase)
	const words = kind === undefined ? phase : WORDS[kind]
	return detail ? `${words} · ${detail}` : words
}
