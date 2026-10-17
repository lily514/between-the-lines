import type { Question } from '../../api/client.ts'

type Delivered = Question['delivered']
type Occurred = Question['occurred']

/** Where play is when the question comes: the heading of the step. Built from the payload's phase, restart and
 * clock only. */
export const stepHeading = (to: Delivered): string => {
	if (to.delivery === 'live') {
		return to.phase === 'dead ball' ? `Play has stopped at ${to.clock}` : `Settled possession at ${to.clock}`
	}
	switch (to.phase) {
		case 'half-time':
			return 'Half-time'
		case 'full time':
			return 'Full time'
		default:
			return to.restart === null
				? `Play has stopped at ${to.clock}`
				: `Play has stopped for a ${to.restart} at ${to.clock}`
	}
}

/** How far the match moved since the last question, or since kick-off. */
export const movedOn = (from: string | null, to: Delivered): string => {
	if (to.phase === 'half-time' || to.phase === 'full time') {
		return from === null ? 'Straight through to the whistle.' : `The match moved on from ${from} to the whistle.`
	}
	return from === null
		? `Kick-off. The match moves on to ${to.clock}.`
		: `The match moves on from ${from} to ${to.clock}.`
}

/** The phase pill's phase: a live question is in settled play, or in the dead ball it asks about. */
export const stepPhase = (to: Delivered): string => {
	if (to.delivery !== 'live') {
		return to.phase
	}
	return to.phase === 'dead ball' ? 'dead ball' : 'settled'
}

/**
 * Why the question is asked now: a live read in settled play or as play stops, or a look back at play saved for this
 * stoppage.
 */
export const whyNow = (to: Delivered, occurred: Occurred): string => {
	if (to.delivery === 'live') {
		return to.phase === 'dead ball'
			? 'Play has just stopped, so there is time to call what happens next.'
			: 'Play has settled, so there is time for a quick read before the next pass.'
	}
	return `A question about the play at ${occurred.clock}, saved until play stopped.`
}
