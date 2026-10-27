import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { Question } from '../../api/client.ts'
import { DEFAULT_PLAYBACK, type Playback } from '../Preferences/index.support.ts'
import './index.css'
import { movedOn, stepHeading, stepPhase, whyNow } from './index.support.ts'
import PhasePill from '../Shared/PhasePill.tsx'
import Commentary from './Commentary.tsx'
import { matchClock, type PlayByPlay } from './Commentary.support.ts'

export interface MatchStepProps {
	home: string
	away: string
	homeCode: string
	awayCode: string
	matchNumber: number
	/** Who had the ball from where the last question left the viewer, or from kick-off, up to this one. */
	play: PlayByPlay
	/** When and where the next question is asked. */
	to: Question['delivered']
	/** When the play the question is about happened. */
	occurred: Question['occurred']
	/** The score as the question comes, from the server. */
	score: string | null
	/** What happened since the viewer's last answer in this match, from the server; null at the first question. */
	catchUp: string | null
	/** Which side is the viewer's team, tagged "You" in the fixture. */
	yours: 'home' | 'away' | null
	/** How fast the match feed plays, and whether demo mode caps each run. */
	playback?: Playback
	/** Where the stream view shows the match feed on a wide screen. */
	streamSlot?: HTMLElement | null
	onArrive: () => void
}

/** Between two questions: the match moves on to the next moment worth asking about, its clock running on and who has
 * the ball called as on the radio. The question shows once the clock reaches it, or when the viewer skips ahead. */
const MatchStep = ({
	home,
	away,
	homeCode,
	awayCode,
	matchNumber,
	play,
	to,
	occurred,
	score,
	catchUp,
	yours,
	streamSlot = null,
	playback = DEFAULT_PLAYBACK,
	onArrive
}: MatchStepProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const [reached, setReached] = useState(false)
	const reach = useCallback(() => {
		setReached(true)
	}, [])

	// The heading changes to the question when the clock reaches it, so focus goes there again to announce it.
	useEffect(() => {
		heading.current?.focus()
	}, [reached])

	const live = to.delivery === 'live'
	// The server's clock starts at 0 only at kick-off: the match's first question has no question before it.
	const from = play.start === 0 ? null : matchClock(play.start)
	return (
		<section className="match-step" aria-labelledby={headingId}>
			<header className="match-step__bar">
				<span className="match-step__chip">Match {matchNumber}</span>
				<span className="match-step__fixture">
					<Club name={home} yours={yours === 'home'} /> v <Club name={away} yours={yours === 'away'} />
				</span>
				<span className="match-step__clock">
					{to.clock}
					{score !== null && ` · ${score}`}
				</span>
			</header>
			{catchUp !== null && (
				<p className="match-step__catch-up">
					<strong>While you were answering:</strong> {catchUp}
				</p>
			)}
			<p className="match-step__moved">{movedOn(from, to)}</p>
			<Commentary
				play={play}
				teams={{ home, away, homeCode, awayCode, yours }}
				streamSlot={streamSlot}
				onReached={reach}
				atQuestion={reached}
				playback={playback}
			/>
			{reached && <PhasePill phase={stepPhase(to)} detail={live ? null : to.restart} />}
			<h2 id={headingId} ref={heading} tabIndex={-1} className="match-step__heading screen-heading">
				{reached ? stepHeading(to) : 'The match plays on'}
			</h2>
			{reached ? (
				<>
					<p className="match-step__why">{whyNow(to, occurred)}</p>
					<button type="button" className="primary-button" onClick={onArrive}>
						{live ? 'Make your read' : 'See the question'}
					</button>
				</>
			) : (
				<button type="button" className="text-button match-step__skip" onClick={reach}>
					Skip to the question
				</button>
			)}
		</section>
	)
}

const Club = ({ name, yours }: { name: string; yours: boolean }) =>
	yours ? (
		<span className="match-step__yours">
			{name} <span className="match-step__you">You</span>
		</span>
	) : (
		<>{name}</>
	)

export default MatchStep
