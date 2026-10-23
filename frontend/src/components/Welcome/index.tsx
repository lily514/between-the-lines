import { useEffect, useId, useRef, type RefObject } from 'react'
import type { Status } from '../../api/client.ts'
import Crest from '../Shared/Crest.tsx'
import ProgressBar from '../Shared/ProgressBar.tsx'
import StartOver from '../Shared/StartOver.tsx'
import { percent } from '../Shared/ProgressBar.support.ts'
import './index.css'

export interface WelcomeProps {
	/** The viewer's record once found, or null before they start. */
	status: Status | null
	/** Why starting failed, as the API said it. */
	error: string | null
	onStart: () => void
	onWatch: () => void
	/** Forget this viewer and start a new one; asked first, since the old record can't be found again. */
	onStartOver: () => void
	/** Go back to the club picker; only offered while the viewer can still change their team. */
	onChangeTeam: () => void
}

/** The start: one button, then where the viewer stands (which match is next, and each concept's bar).
 *
 * There is no sign-in: the page makes the viewer a random id and keeps it in this browser. */
const Welcome = ({ status, error, onStart, onWatch, onStartOver, onChangeTeam }: WelcomeProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [status])

	return (
		<section className="welcome" aria-labelledby={headingId}>
			{status === null ? (
				<Start headingId={headingId} heading={heading} error={error} onStart={onStart} />
			) : (
				<>
					<h2 id={headingId} ref={heading} tabIndex={-1} className="welcome__heading screen-heading">
						{status.finished ? 'All three matches watched' : 'Welcome'}
					</h2>
					{status.club !== null && (
						<p className="welcome__team">
							<Crest code={status.club.code} size={24} />
							<span>
								Your team: <strong>{status.club.name}</strong>
							</span>
							{status.can_choose_club && (
								<button type="button" className="text-button" onClick={onChangeTeam}>
									Change
								</button>
							)}
						</p>
					)}
					{status.fixture !== null && (
						<p className="welcome__next">
							Match <span className="welcome__number">{status.match_number}</span> of{' '}
							<span className="welcome__number">{status.matches}</span>: {status.fixture.home} v{' '}
							{status.fixture.away}
						</p>
					)}
					<ul className="welcome__bars" aria-label="Your understanding so far">
						{status.concepts.map(concept => (
							<li key={concept.name}>
								<p className="welcome__concept">
									{concept.name} <span className="welcome__number">{percent(concept.value)}%</span>
								</p>
								<ProgressBar
									name={concept.name}
									before={concept.value}
									after={concept.value}
									unlock={status.thresholds.unlock}
									mastery={status.thresholds.mastery}
								/>
							</li>
						))}
					</ul>
					{!status.finished && (
						<button type="button" className="primary-button" onClick={onWatch}>
							Watch match {status.match_number}
						</button>
					)}
					<div className="welcome__change">
						<StartOver
							label={status.finished ? 'Start again with new matches' : 'Start over'}
							onConfirm={onStartOver}
						/>
					</div>
				</>
			)}
		</section>
	)
}

interface StartProps {
	headingId: string
	heading: RefObject<HTMLHeadingElement | null>
	error: string | null
	onStart: () => void
}

const Start = ({ headingId, heading, error, onStart }: StartProps) => (
	<div className="welcome__start">
		<h2 id={headingId} ref={heading} tabIndex={-1} className="welcome__heading screen-heading">
			Watch three matches, one question at a time
		</h2>
		<p className="welcome__intro">
			Now and then, when play allows, you get a question about what just happened on the pitch. Your answers shape
			the questions that follow.
		</p>
		<p className="welcome__hint">No sign-in: this browser keeps your place, so you can come back to it.</p>
		{error !== null && (
			<p className="welcome__error" role="alert">
				{error}
			</p>
		)}
		<button type="button" className="primary-button" onClick={onStart}>
			Start
		</button>
	</div>
)

export default Welcome
