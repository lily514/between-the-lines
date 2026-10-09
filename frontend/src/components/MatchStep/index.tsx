import { useEffect, useId, useRef } from 'react'
import type { Question } from '../../api/client.ts'
import './index.css'
import { movedOn, stepHeading, whyNow } from './index.support.ts'
import PhasePill from '../Shared/PhasePill.tsx'

export interface MatchStepProps {
	home: string
	away: string
	matchNumber: number
	/** The clock where the last question left the viewer, or null at kick-off. */
	from: string | null
	/** When and where the next question is asked. */
	to: Question['delivered']
	/** When the play the question is about happened. */
	occurred: Question['occurred']
	/** The score at a live question; a review question's score may be out of date, so it has none. */
	score: string | null
	onArrive: () => void
}

/** Between two questions: the match moves on to the next moment worth asking about.
 *
 * It takes a span of match time (`from` → `to`) rather than a question, so a component that plays the match at speed
 * can take its place with the same props and call `onArrive` when the clock gets there. */
const MatchStep = ({ home, away, matchNumber, from, to, occurred, score, onArrive }: MatchStepProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	const live = to.delivery === 'live'
	return (
		<section className="match-step" aria-labelledby={headingId}>
			<header className="match-step__bar">
				<span className="match-step__chip">Match {matchNumber}</span>
				<span className="match-step__fixture">
					{home} v {away}
				</span>
				<span className="match-step__clock">
					{to.clock}
					{score !== null && ` · ${score}`}
				</span>
			</header>
			<p className="match-step__moved">{movedOn(from, to)}</p>
			<PhasePill phase={live ? 'settled' : to.phase} detail={live ? null : to.restart} />
			<h2 id={headingId} ref={heading} tabIndex={-1} className="match-step__heading screen-heading">
				{stepHeading(to)}
			</h2>
			<p className="match-step__why">{whyNow(to, occurred)}</p>
			<button type="button" className="primary-button" onClick={onArrive}>
				{live ? 'Make your read' : 'See the question'}
			</button>
		</section>
	)
}

export default MatchStep
