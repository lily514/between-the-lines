import { useEffect, useId, useRef } from 'react'
import type { Report as ReportData } from '../../api/client.ts'
import PhasePill from '../Shared/PhasePill.tsx'
import ProgressBar from '../Shared/ProgressBar.tsx'
import { percent } from '../Shared/ProgressBar.support.ts'
import Radar from '../Shared/Radar.tsx'
import { byStrand, resultLine } from './index.support.ts'
import './index.css'

export interface ReportProps {
	report: ReportData
	/** On to the second half at halftime; back to Matches at full time. */
	onContinue: () => void
	/** Open the curriculum map. */
	onMap: () => void
}

/** The scouting report at halftime or full time (S6): the score and goals, the radar, the scout's note, each concept
 * asked about now by strand, and the questions answered. Every number comes from the report. */
const Report = ({ report, onContinue, onMap }: ReportProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [report])

	const halftime = report.at === 'halftime'
	const span = halftime ? 'this half' : 'this match'
	const result = resultLine(report)
	return (
		<section className="report" aria-labelledby={headingId}>
			<header className="report__bar">
				<PhasePill phase={halftime ? 'half-time' : 'full time'} />
				<span className="report__chip">Match {report.match_number}</span>
			</header>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="report__score screen-heading">
				{report.home} <span className="report__goals">{report.home_goals}</span>–
				<span className="report__goals">{report.away_goals}</span> {report.away}
			</h2>
			{result !== null && <p className="report__result">{result}</p>}
			{report.goals.length > 0 && (
				<ol className="report__goals-list" aria-label="Goals">
					{report.goals.map(goal => (
						<li key={`${goal.clock}-${goal.scorer}`}>
							<span className="report__clock">{goal.clock}</span>
							<span>
								Goal, {goal.side === 'home' ? report.home : report.away} · {goal.scorer}
								{goal.own_goal && ' (own goal)'}
							</span>
						</li>
					))}
				</ol>
			)}

			<section className="report__card" aria-label="Your scouting report">
				<h3 className="report__section">Your scouting report</h3>
				<p className="report__sub">{halftime ? 'Kick-off to halftime.' : 'Kick-off to full time.'}</p>
				<Radar strands={report.strands} nowLabel={halftime ? 'Halftime' : 'Full time'} />
				<div className="report__note">
					<p className="report__note-head">Scout’s note</p>
					<p className="report__note-text">{report.note}</p>
				</div>
			</section>

			<section aria-label="What you’re being asked">
				<h3 className="report__section">What you’re being asked</h3>
				<p className="report__sub">The concepts questions cover today, by strand.</p>
				{byStrand(report).map(strand => (
					<div key={strand.key} className="report__strand">
						<p className="report__strand-name">{strand.name}</p>
						{strand.concepts.length === 0 ? (
							<p className="report__later">
								No questions yet. {strand.name} concepts are coming later, so this strand has no score.
							</p>
						) : (
							<ul className="report__concepts">
								{strand.concepts.map(concept => (
									<li key={concept.name}>
										<p className="report__concept">
											<span>{concept.name}</span>
											<span className="report__level">
												{concept.mastered && <span aria-hidden="true">✓ </span>}
												{concept.level}{' '}
												<span className="report__number">{percent(concept.after)}%</span>
											</span>
										</p>
										<ProgressBar
											name={concept.name}
											before={concept.before}
											after={concept.after}
											unlock={report.thresholds.unlock}
											mastery={report.thresholds.mastery}
										/>
									</li>
								))}
							</ul>
						)}
					</div>
				))}
				<button type="button" className="text-button report__map" onClick={onMap}>
					See your full map
				</button>
			</section>

			<section aria-label={`Questions ${span}`}>
				<h3 className="report__section">Questions {span}</h3>
				{report.answers.length === 0 ? (
					<p className="report__sub">No questions {span}. The report reads fine without them.</p>
				) : (
					<>
						<p className="report__sub">
							<span className="report__number">{report.right}</span> of{' '}
							<span className="report__number">{report.answers.length}</span> right.
						</p>
						<ul className="report__answers">
							{report.answers.map((line, i) => (
								<li
									key={`${line.clock}-${String(i)}`}
									className={line.correct ? 'report__answer--right' : ''}>
									<span className="report__clock">{line.clock}</span>
									<span>{line.concept}</span>
									<span className="report__mark">
										<span aria-hidden="true">{line.correct ? '✓' : '✕'}</span>{' '}
										{line.correct ? 'Right read' : 'Not this one'}
									</span>
								</li>
							))}
						</ul>
					</>
				)}
			</section>

			<button type="button" className="primary-button" onClick={onContinue}>
				{halftime ? 'Ready for the second half' : 'Done for this match'}
			</button>
			{!halftime && <p className="report__after">Back to Matches.</p>}
		</section>
	)
}

export default Report
