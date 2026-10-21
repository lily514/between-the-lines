import { useEffect, useId, useRef } from 'react'
import type { FullTime as FullTimeData } from '../../api/client.ts'
import './index.css'
import PhasePill from '../Shared/PhasePill.tsx'
import ProgressBar from '../Shared/ProgressBar.tsx'
import { percent } from '../Shared/ProgressBar.support.ts'
import { resultLine } from './index.support.ts'

export interface FullTimeProps {
	summary: FullTimeData
	onNext: () => void
}

/** The full-time summary: the score, how many questions were asked, and each concept from kick-off to now. */
const FullTime = ({ summary, onNext }: FullTimeProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="full-time" aria-labelledby={headingId}>
			<header className="full-time__bar">
				<PhasePill phase="full time" />
				<span className="full-time__chip">Match {summary.match_number}</span>
			</header>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="full-time__score screen-heading">
				{summary.home} <span className="full-time__goals">{summary.home_goals}</span>–
				<span className="full-time__goals">{summary.away_goals}</span> {summary.away}
			</h2>
			{resultLine(summary) !== null && <p className="full-time__result">{resultLine(summary)}</p>}
			<p className="full-time__questions">
				<span className="full-time__number">{summary.questions}</span>{' '}
				{summary.questions === 1 ? 'question' : 'questions'} this match.
			</p>
			<ul className="full-time__concepts" aria-label="Your understanding, kick-off to now">
				{summary.concepts.map(concept => (
					<li key={concept.name}>
						<p className="full-time__concept">
							{concept.name}: <span className="full-time__number">{percent(concept.before)}%</span> →{' '}
							<span className="full-time__number full-time__number--now">{percent(concept.after)}%</span>
						</p>
						<ProgressBar
							name={concept.name}
							before={concept.before}
							after={concept.after}
							unlock={summary.thresholds.unlock}
							mastery={summary.thresholds.mastery}
						/>
					</li>
				))}
			</ul>
			{summary.finished && <p className="full-time__done">You’ve watched all three matches.</p>}
			<button type="button" className="primary-button" onClick={onNext}>
				{summary.next_match === null ? 'See where you stand' : `On to match ${String(summary.next_match)}`}
			</button>
		</section>
	)
}

export default FullTime
