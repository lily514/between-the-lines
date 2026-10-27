import type { Point } from '../Shared/Pitch/index.support.ts'
import type { PlayByPlay } from './Commentary.support.ts'

export type Track = PlayByPlay['track']

export interface PitchPlayer {
	shirt: number
	home: boolean
	/** Where they are, in picture coordinates. */
	at: Point
	onBall: boolean
}

/** The pitch at one instant: the players whose positions are known, and the ball. */
export interface PitchNow {
	players: PitchPlayer[]
	ball: Point
}

interface Timed {
	period: number
	at: number
}

/** The latest keyframe at or before the clock, as the commentary picks the latest touch, the next one if it is in the
 * same period, and how far the clock has got from one to the other, from 0 to 1. */
const segment = <T extends Timed>(points: readonly T[], at: number): { from: T; to?: T; share: number } | null => {
	const from = points.findLast(point => point.at <= at) ?? points.at(0)
	if (from === undefined) {
		return null
	}
	const to = points.at(points.indexOf(from) + 1)
	if (to?.period !== from.period || to.at <= from.at || at <= from.at) {
		return { from, share: 0 }
	}
	return { from, to, share: (at - from.at) / (to.at - from.at) }
}

const ease = (share: number) => share * share * (3 - 2 * share)

const blend = (from: Point, to: Point, share: number): Point => [
	from[0] + (to[0] - from[0]) * share,
	from[1] + (to[1] - from[1]) * share
]

/**
 * Where the players and the ball are `at` seconds on the match clock, from the server's keyframes. Players ease
 * between keyframes and the ball moves steadily, never across a period change. With `smooth` off (reduced motion)
 * both jump from keyframe to keyframe. Before the first keyframe the pitch is at the first, and after the last it
 * stays on the last. Null when there is nothing to draw.
 */
export const trackAt = (track: Track, at: number, smooth = true): PitchNow | null => {
	const frames = segment(track.frames, at)
	const ball = segment(track.ball, at)
	if (frames === null || ball === null) {
		return null
	}
	const moving = smooth ? ease(frames.share) : 0
	const players = track.players.flatMap((player, index) => {
		const from = frames.from.positions[index] ?? null
		if (from === null) {
			return []
		}
		// Where the next position is unknown, the player stays put.
		const to = frames.to?.positions[index] ?? from
		return [{ ...player, at: blend(from, to, moving), onBall: frames.from.on_ball === index }]
	})
	const along = smooth && ball.to !== undefined ? ball.share : 0
	return { players, ball: blend(ball.from.point, (ball.to ?? ball.from).point, along) }
}
