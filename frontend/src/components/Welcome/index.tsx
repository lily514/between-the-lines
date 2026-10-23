import { useEffect, useId, useRef } from 'react'
import type { ConceptMap } from '../../api/client.ts'
import { askedNow } from './index.support.ts'
import './index.css'

export interface WelcomeProps {
	/** The curriculum, for what the questions cover; null while it loads. */
	curriculum: ConceptMap | null
	/** Why starting failed, as the API said it. */
	error: string | null
	onStart: () => void
	/** Open the map of all the concepts. */
	onSeeAll: () => void
}

/** The first screen: what the questions cover, by strand, and where everyone starts. Then the club picker.
 *
 * There is no sign-in: the page makes the viewer a random id and keeps it in this browser. */
const Welcome = ({ curriculum, error, onStart, onSeeAll }: WelcomeProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	const groups = curriculum === null ? [] : askedNow(curriculum)
	const asked = groups.reduce((total, group) => total + group.concepts.length, 0)
	return (
		<section className="welcome" aria-labelledby={headingId}>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="welcome__heading screen-heading">
				Watch the match. We’ll help you read it.
			</h2>
			<p className="welcome__intro">
				A handful of questions as the game goes on, one at a time
				{curriculum === null ? '.' : `. For now they cover ${String(asked)} things.`}
			</p>
			{groups.map(group => (
				<section key={group.key} className="welcome__strand" aria-label={group.name}>
					<h3 className="welcome__strand-name">
						{group.name}{' '}
						<span className="welcome__count">
							{group.concepts.length === 0 ? 'Coming later' : `${String(group.concepts.length)} to start`}
						</span>
					</h3>
					{group.concepts.length === 0 ? (
						<p className="welcome__later">No questions yet.</p>
					) : (
						<ul className="welcome__concepts">
							{group.concepts.map(concept => (
								<li key={concept.key}>
									<span className="welcome__concept">{concept.name}</span>
									<span className="welcome__objective">{concept.objective}</span>
								</li>
							))}
						</ul>
					)}
				</section>
			))}
			<p className="welcome__start-level">
				Everyone starts at <strong>Getting there</strong>. Your answers take you to Solid, then Sharp. No test
				first.
			</p>
			<button type="button" className="text-button welcome__all" onClick={onSeeAll}>
				See all {curriculum === null ? '' : `${String(curriculum.concepts.length)} `}concepts, including what’s
				coming later
			</button>
			<p className="welcome__hint">No sign-in: this browser keeps your place, so you can come back to it.</p>
			{error !== null && (
				<p className="welcome__error" role="alert">
					{error}
				</p>
			)}
			<button type="button" className="primary-button" onClick={onStart}>
				Continue
			</button>
		</section>
	)
}

export default Welcome
