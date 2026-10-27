import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { clockAt, heardAt, matchClock, runMs, timeLeft, type PlayByPlay } from './Commentary.support.ts'
import './Commentary.css'

export interface CommentaryProps {
	play: PlayByPlay
	home: string
	away: string
	/** Where the stream view shows the commentary on a wide screen; the panel's own copy is then for screen readers
	 * only. */
	streamSlot?: HTMLElement | null
}

/** The match as a radio listener follows it between questions: the clock running on to the next question, who is on
 * the ball, and the spells of possession so far. Everything it says comes from the play-by-play the server sent. */
const Commentary = ({ play, home, away, streamSlot = null }: CommentaryProps) => {
	const [at, setAt] = useState(play.start)

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

	const { onBall, log } = heardAt(play, at)
	const team = (side: 'home' | 'away') => (side === 'home' ? home : away)
	// The panel's copy is the one screen readers hear, so only it is named; the stream view is hidden from them.
	const body = (panel: boolean) => (
		<>
			<div className="commentary__clocks">
				<span className="commentary__clock" {...(panel ? { role: 'timer', 'aria-label': 'Match clock' } : {})}>
					{matchClock(at)}
				</span>
				<span className="commentary__countdown">
					{at < play.end ? `Next question in ${timeLeft(play.end - at)}` : 'Question time'}
				</span>
			</div>
			<p className="commentary__on-ball">
				{onBall === null ? (
					'Play goes on.'
				) : (
					<>
						<span className={`commentary__team commentary__team--${onBall.side}`}>{team(onBall.side)}</span>{' '}
						on the ball:{' '}
						<span className="commentary__player">
							#{onBall.touch.number} {onBall.touch.surname}
						</span>
					</>
				)}
			</p>
			{log.length > 0 && (
				<ol className="commentary__log" {...(panel ? { 'aria-label': 'Who has had the ball' } : {})}>
					{log.map(line => (
						<li key={line.index}>
							<span className="commentary__log-clock">{line.clock}</span>{' '}
							<span className={`commentary__team commentary__team--${line.side}`}>{team(line.side)}</span>
							: {line.names.join(', ')}
						</li>
					))}
				</ol>
			)}
		</>
	)
	return (
		<>
			<div className={streamSlot === null ? 'commentary' : 'commentary commentary--streamed'}>{body(true)}</div>
			{streamSlot !== null &&
				createPortal(<div className="commentary commentary--stream">{body(false)}</div>, streamSlot)}
		</>
	)
}

export default Commentary
