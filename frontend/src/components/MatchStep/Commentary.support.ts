import type { Question } from '../../api/client.ts'

export type PlayByPlay = Question['play_by_play']
type Side = PlayByPlay['spells'][number]['side']
type Touch = PlayByPlay['spells'][number]['touches'][number]

/** The clock runs at a minute of match time per 1.5 s, sped up so no run takes longer than 20 s. */
const MS_PER_MATCH_MINUTE = 1500
const LONGEST_RUN_MS = 20_000
/** How many spells the log keeps: the one under way and those just before it. */
export const LOG_SPELLS = 4

/** How long the page takes to play the match from where the viewer left off to the next question. */
export const runMs = (play: PlayByPlay): number =>
	Math.min(LONGEST_RUN_MS, (Math.max(0, play.end - play.start) / 60) * MS_PER_MATCH_MINUTE)

/** Seconds on the match clock after `elapsed` ms of a run that takes `run` ms. */
export const clockAt = (play: PlayByPlay, elapsed: number, run: number): number =>
	run <= 0 ? play.end : play.start + (play.end - play.start) * Math.min(1, elapsed / run)

/** Seconds as the match clock shows them, e.g. 68:12, cut to the second as the server does. */
export const matchClock = (seconds: number): string => {
	const whole = Math.floor(seconds)
	return `${String(Math.floor(whole / 60)).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`
}

/** Match time left, e.g. 2:05. */
export const timeLeft = (seconds: number): string => {
	const whole = Math.ceil(seconds)
	return `${String(Math.floor(whole / 60))}:${String(whole % 60).padStart(2, '0')}`
}

export interface LogLine {
	/** Which of the play-by-play's spells this is. */
	index: number
	side: Side
	clock: string
	/** Who has touched the ball so far in the spell, by surname, without the same name twice in a row. */
	names: string[]
}

export interface Heard {
	/** Who is on the ball now; null before the first touch, and in play the play-by-play doesn't name. */
	onBall: { side: Side; touch: Touch } | null
	/** The spells so far, newest first. */
	log: LogLine[]
}

/** What a listener has heard by `at` seconds on the match clock. */
export const heardAt = (play: PlayByPlay, at: number): Heard => {
	const started = play.spells
		.map((spell, index) => ({ ...spell, index, touches: spell.touches.filter(touch => touch.at <= at) }))
		.filter(spell => spell.touches.length > 0)
	const current = started.at(-1)
	const touch = current?.touches.at(-1)
	const unnamed = at >= play.names_until && play.names_until < play.end
	return {
		onBall: current === undefined || touch === undefined || unnamed ? null : { side: current.side, touch },
		log: started
			.slice(-LOG_SPELLS)
			.reverse()
			.map(spell => ({
				index: spell.index,
				side: spell.side,
				clock: matchClock(spell.touches[0]?.at ?? at),
				names: spell.touches.map(t => t.surname).filter((name, i, names) => i === 0 || name !== names[i - 1])
			}))
	}
}
