import { useEffect, useId, useRef, useState, type RefObject, type SyntheticEvent } from 'react'
import type { Status } from '../../api/client.ts'
import ProgressBar from '../Shared/ProgressBar.tsx'
import { percent } from '../Shared/ProgressBar.support.ts'
import './index.css'

export interface WelcomeProps {
	/** The viewer's record once found, or null while they type their name. */
	status: Status | null
	/** Why the last name was refused, as the API said it. */
	error: string | null
	/** The name to start with: the one this browser remembers, if any. */
	defaultName: string
	onStart: (name: string) => void
	onWatch: () => void
	onChangeName: () => void
}

/** The start: a name, then where the viewer stands (which match is next, and each concept's bar). */
const Welcome = ({ status, error, defaultName, onStart, onWatch, onChangeName }: WelcomeProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [status])

	return (
		<section className="welcome" aria-labelledby={headingId}>
			{status === null ? (
				<NameForm
					headingId={headingId}
					heading={heading}
					error={error}
					defaultName={defaultName}
					onStart={onStart}
				/>
			) : (
				<>
					<h2 id={headingId} ref={heading} tabIndex={-1} className="welcome__heading screen-heading">
						{status.finished
							? `All three matches watched, ${status.viewer_id}`
							: `Welcome, ${status.viewer_id}`}
					</h2>
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
					<button type="button" className="text-button welcome__change" onClick={onChangeName}>
						{status.finished
							? 'Start again with another name'
							: `Not ${status.viewer_id}? Use another name`}
					</button>
				</>
			)}
		</section>
	)
}

interface NameFormProps {
	headingId: string
	heading: RefObject<HTMLHeadingElement | null>
	error: string | null
	defaultName: string
	onStart: (name: string) => void
}

const NameForm = ({ headingId, heading, error, defaultName, onStart }: NameFormProps) => {
	const [name, setName] = useState(defaultName)
	const inputId = useId()
	const hintId = useId()
	const errorId = useId()

	const onSubmit = (event: SyntheticEvent<HTMLFormElement>) => {
		event.preventDefault()
		const trimmed = name.trim()
		if (trimmed !== '') {
			onStart(trimmed)
		}
	}

	return (
		<form className="welcome__form" onSubmit={onSubmit} noValidate>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="welcome__heading screen-heading">
				Watch three matches, one question at a time
			</h2>
			<p className="welcome__intro">
				Now and then, when play allows, you get a question about what just happened on the pitch. Your answers
				shape the questions that follow.
			</p>
			<label htmlFor={inputId} className="welcome__label">
				Your name
			</label>
			<input
				id={inputId}
				className="welcome__input"
				value={name}
				onChange={event => {
					setName(event.target.value.toLowerCase())
				}}
				autoComplete="nickname"
				autoCapitalize="none"
				spellCheck={false}
				aria-describedby={error === null ? hintId : `${hintId} ${errorId}`}
				aria-invalid={error !== null}
			/>
			<p id={hintId} className="welcome__hint">
				Lower-case letters and digits; it keeps your place between visits.
			</p>
			{error !== null && (
				<p id={errorId} className="welcome__error" role="alert">
					{error}
				</p>
			)}
			<button type="submit" className="primary-button" aria-disabled={name.trim() === ''}>
				Start
			</button>
		</form>
	)
}

export default Welcome
