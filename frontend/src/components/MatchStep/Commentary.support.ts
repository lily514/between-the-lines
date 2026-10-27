import type { Question } from '../../api/client.ts'

export type PlayByPlay = Question['play_by_play']
export type Side = PlayByPlay['spells'][number]['side']
export type Touch = PlayByPlay['spells'][number]['touches'][number]
export type FeedEntry = PlayByPlay['feed'][number]
export type Stats = PlayByPlay['stats'][number]

/** The clock runs at a minute of match time per 1.5 s, sped up so no run takes longer than 20 s. */
const MS_PER_MATCH_MINUTE = 1500
const LONGEST_RUN_MS = 20_000

/** How long the page takes to play the match from where the viewer left off to the next question. */
export const runMs = (play: PlayByPlay): number =>
	Math.min(LONGEST_RUN_MS, (Math.max(0, play.end - play.start) / 60) * MS_PER_MATCH_MINUTE)

/** How many times faster than real time the run plays the match, e.g. 40; null when there is nothing to play. */
export const playbackSpeed = (play: PlayByPlay): number | null => {
	const run = runMs(play)
	return run <= 0 ? null : Math.round((play.end - play.start) / (run / 1000))
}

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

export interface Heard {
	/** Who is on the ball now; null before the first touch, and in play the play-by-play doesn't name. */
	onBall: { side: Side; touch: Touch } | null
	/** The feed so far, newest first: each entry once the clock reaches its `until`. */
	feed: FeedEntry[]
	/** The match's numbers as they stand; the first entry until the clock reaches it. */
	stats: Stats | null
}

/** What a listener has heard by `at` seconds on the match clock. */
export const heardAt = (play: PlayByPlay, at: number): Heard => {
	const started = play.spells
		.map(spell => ({ ...spell, touches: spell.touches.filter(touch => touch.at <= at) }))
		.filter(spell => spell.touches.length > 0)
	const current = started.at(-1)
	const touch = current?.touches.at(-1)
	const unnamed = at >= play.names_until && play.names_until < play.end
	return {
		onBall: current === undefined || touch === undefined || unnamed ? null : { side: current.side, touch },
		feed: play.feed.filter(entry => entry.until <= at).reverse(),
		stats: play.stats.findLast(entry => entry.at <= at) ?? play.stats[0] ?? null
	}
}

/** The two clubs as the feed names them, and which one is the viewer's. */
export interface Teams {
	home: string
	away: string
	homeCode: string
	awayCode: string
	yours: Side | null
}

export const codeOf = (teams: Teams, side: Side): string => (side === 'home' ? teams.homeCode : teams.awayCode)

/** The half a stats entry is in, as the scorebug says it. */
export const halfWord = (period: number): string => (period === 2 ? '2nd half' : '1st half')

/** An entry's line on its own: its words, or a move's players in turn. */
export const entrySummary = (entry: FeedEntry): string =>
	[entry.text, entry.names.join(' → ')].filter(part => part !== '').join(' ')
