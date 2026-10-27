import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import {
	clockAt,
	codeOf,
	entrySummary,
	heardAt,
	matchClock,
	runMs,
	timeLeft,
	type PlayByPlay,
	type Teams
} from './Commentary.support.ts'
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
}

/** The match between questions, as a text feed follows it: the clock running on to the next question, the score and
 * numbers, who is on the ball and what they do with it, and the feed from kick-off. Everything it says comes from the
 * play-by-play the server sent. In the panel it is the phone's compact version, with the rest in a sheet. */
const Commentary = ({ play, teams, streamSlot = null }: CommentaryProps) => {
	const [at, setAt] = useState(play.start)
	const [notesOpen, setNotesOpen] = useState(false)

	useEffect(() => {
		const run = runMs(play)
		const began = performance.now()
		let frame = 0
		const tick = (now: number) => {
			const next = clockAt(play, now - began, run)
			setAt(next)
			if (next < play.end) frame = requestAnimationFrame(tick)
		}
		frame = requestAnimationFrame(tick)
		return () => {
			cancelAnimationFrame(frame)
		}
	}, [play])

	const heard = heardAt(play, at)
	const clock = matchClock(at)
	const asked = at >= play.end
	const countdown = asked ? 'Question time' : `Next question in ${timeLeft(play.end - at)}`
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
					<MatchFeed teams={teams} heard={heard} clock={clock} countdown={countdown} asked={asked} />,
					streamSlot
				)}
		</>
	)
}

export default Commentary
