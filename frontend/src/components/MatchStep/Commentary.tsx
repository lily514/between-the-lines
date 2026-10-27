import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
	clockAt,
	codeOf,
	entrySummary,
	heardAt,
	matchClock,
	playbackSpeed,
	runMs,
	timeLeft,
	type PlayByPlay,
	type Teams
} from './Commentary.support.ts'
import { DEFAULT_PLAYBACK, type Playback } from '../Preferences/index.support.ts'
import EarlierNotes from './EarlierNotes.tsx'
import MatchFeed from './MatchFeed.tsx'
import NowCard from './NowCard.tsx'
import Scorebug from './Scorebug.tsx'
import SideMark from './SideMark.tsx'
import './Commentary.css'

export interface CommentaryProps {
	play: PlayByPlay
	teams: Teams
	/** Where the stream view shows the match feed on a wide screen; the panel's own copy is then for screen readers
	 * only. */
	streamSlot?: HTMLElement | null
	/** Called once, when the clock reaches the moment the next question is asked. Keep it stable: a new one restarts
	 * the clock. */
	onReached?: () => void
	/** The question is showing, so the clock stands at its moment: a skip ahead jumps the feed there too. */
	atQuestion?: boolean
	/** How fast the feed plays, and whether demo mode caps each run. */
	playback?: Playback
}

/** The match between questions, as a text feed follows it: the clock running on to the next question, the score and
 * numbers, who is on the ball and what they do with it, and the feed from kick-off. Everything it says comes from the
 * play-by-play the server sent. In the panel it is the phone's compact version, with the rest in a sheet. */
const Commentary = ({
	play,
	teams,
	streamSlot = null,
	onReached,
	atQuestion = false,
	playback = DEFAULT_PLAYBACK
}: CommentaryProps) => {
	const [at, setAt] = useState(play.start)
	const [notesOpen, setNotesOpen] = useState(false)
	// Where the clock has got to, so a change of speed carries on from there rather than starting the run again.
	const progress = useRef({ play, at: play.start })

	useEffect(() => {
		if (atQuestion) return
		const from = progress.current.play === play ? progress.current.at : play.start
		const rest = { ...play, start: from }
		const run = runMs(rest, playback)
		const began = performance.now()
		let frame = 0
		const tick = (now: number) => {
			const next = clockAt(rest, now - began, run)
			progress.current = { play, at: next }
			setAt(next)
			if (next < play.end) frame = requestAnimationFrame(tick)
			else onReached?.()
		}
		frame = requestAnimationFrame(tick)
		return () => {
			cancelAnimationFrame(frame)
		}
	}, [play, playback, onReached, atQuestion])

	// Once the question shows the clock stands at its moment, even if the run hadn't got there.
	const now = atQuestion ? play.end : at
	const heard = heardAt(play, now)
	const clock = matchClock(now)
	const asked = now >= play.end
	const countdown = asked ? 'Question time' : `Next question in ${timeLeft(play.end - now)}`
	const latest = heard.feed[0]
	return (
		<>
			<div className={streamSlot === null ? 'commentary' : 'commentary commentary--streamed'}>
				<Scorebug teams={teams} stats={heard.stats} clock={clock} countdown={countdown} compact />
				<NowCard teams={teams} clock={clock} onBall={heard.onBall} asked={asked} compact />
				{latest !== undefined && (
					<p className="commentary__older">
						<span className="commentary__older-clock">{matchClock(latest.at)}</span>
						{latest.side !== null && (
							<>
								<SideMark side={latest.side} />
								{codeOf(teams, latest.side)} ·
							</>
						)}{' '}
						{latest.kind === 'move' ? entrySummary(latest) : `${latest.label}: ${entrySummary(latest)}`}
					</p>
				)}
				<button
					type="button"
					className="text-button commentary__notes"
					onClick={() => {
						setNotesOpen(true)
					}}>
					Earlier notes and stats
				</button>
				{notesOpen && (
					<EarlierNotes
						teams={teams}
						heard={heard}
						clock={clock}
						onClose={() => {
							setNotesOpen(false)
						}}
					/>
				)}
			</div>
			{streamSlot !== null &&
				createPortal(
					<MatchFeed
						teams={teams}
						heard={heard}
						clock={clock}
						countdown={countdown}
						asked={asked}
						speed={playbackSpeed(play, playback)}
						track={play.track}
						at={now}
					/>,
					streamSlot
				)}
		</>
	)
}

export default Commentary
