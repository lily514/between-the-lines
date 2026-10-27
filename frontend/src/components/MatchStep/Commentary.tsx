import { useEffect, useState } from 'react'
import { clockAt, heardAt, matchClock, runMs, timeLeft, type PlayByPlay } from './Commentary.support.ts'
import './Commentary.css'

export interface CommentaryProps {
	play: PlayByPlay
	home: string
	away: string
}

/** The match as a radio listener follows it between questions: the clock running on to the next question, who is on
 * the ball, and the spells of possession so far. Everything it says comes from the play-by-play the server sent. */
const Commentary = ({ play, home, away }: CommentaryProps) => {
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
	return (
		<div className="commentary">
			<div className="commentary__clocks">
				<span className="commentary__clock" role="timer" aria-label="Match clock">
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
							#{onBall.touch.number} {onBall.touch.player}
						</span>
					</>
				)}
			</p>
			{log.length > 0 && (
				<ol className="commentary__log" aria-label="Who has had the ball">
					{log.map(line => (
						<li key={line.index}>
							<span className="commentary__log-clock">{line.clock}</span>{' '}
							<span className={`commentary__team commentary__team--${line.side}`}>{team(line.side)}</span>
							: {line.names.join(', ')}
						</li>
					))}
				</ol>
			)}
		</div>
	)
}

export default Commentary
