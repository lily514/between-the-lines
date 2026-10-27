import { useEffect, useId, useRef } from 'react'
import type { Feedback as FeedbackData, Question } from '../../api/client.ts'
import AnswerGroup from '../Shared/AnswerGroup/index.tsx'
import './index.css'
import { askedConcept, pickedLine, sourceLine, statTiles } from './index.support.ts'
import LevelWord from '../Shared/LevelWord.tsx'
import Pitch from '../Shared/Pitch/index.tsx'
import ProgressBar from '../Shared/ProgressBar.tsx'
import { percent } from '../Shared/ProgressBar.support.ts'
import { pitchOptions } from '../Shared/Pitch/index.support.ts'
import StatTile from './StatTile.tsx'
import VerdictMark from './VerdictMark.tsx'

export interface FeedbackProps {
	feedback: FeedbackData
	/** The question that was answered, for the clock and the options' places on the pitch. */
	question: Question
	onContinue: () => void
}

/** The reveal (S4): the real play drawn on the pitch, then the verdict, the explanation, the measured facts, where
 * they came from, and how the learner model moved. A wrong answer adds the concept's common mix-up. */
const Feedback = ({ feedback, question, onContinue }: FeedbackProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const concept = askedConcept(feedback)
	const stats = statTiles(feedback)

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="feedback" aria-labelledby={headingId}>
			<header className="feedback__bar">
				<span className="feedback__chip">The reveal</span>
				<span className="feedback__clock">{question.delivered.clock}</span>
			</header>
			<div className="feedback__verdict feedback__after-path">
				<VerdictMark kind={feedback.correct ? 'correct' : 'incorrect'} />
				<div>
					<h2 id={headingId} ref={heading} tabIndex={-1} className="feedback__verdict-text">
						{feedback.verdict}
					</h2>
					<p className="feedback__picked">{pickedLine(feedback)}</p>
				</div>
			</div>
			<div className="feedback__pitch">
				<Pitch
					picture={feedback.picture}
					options={pitchOptions(question)}
					path={feedback.reveal_path}
					line={feedback.reveal_line}
					reveal
					crop="moment"
					label={`The real play from ${question.occurred.clock}`}
					yours={question.your_team}
				/>
			</div>
			<AnswerGroup
				label="Your answer"
				choices={feedback.options}
				selected={feedback.chosen}
				onSelect={() => undefined}
				outcome={{ correct: feedback.correct_key, chosen: feedback.chosen ?? '' }}
			/>
			<div className="feedback__copy feedback__after-path" aria-live="polite">
				<p className="feedback__explanation">{feedback.explanation}</p>
				{feedback.misconception !== null && (
					<aside className="feedback__mix-up" aria-label="Common mix-up">
						<VerdictMark kind="mix-up" />
						<div>
							<p className="feedback__mix-up-label">Common mix-up</p>
							<p className="feedback__mix-up-text">“{feedback.misconception}”</p>
						</div>
					</aside>
				)}
				<p className="feedback__takeaway">
					<span className="feedback__takeaway-label">Takeaway</span> {feedback.takeaway}
				</p>
				{stats.length > 0 && (
					<dl className="feedback__stats" aria-label="Computed from match data">
						{stats.map(stat => (
							<StatTile key={stat.key} label={stat.label} value={stat.value} {...unitOf(stat.unit)} />
						))}
					</dl>
				)}
				<p className="feedback__source">{sourceLine(feedback)}</p>
				{concept !== undefined && (
					<section className="feedback__understanding" aria-label="Your understanding">
						<p className="feedback__movement">
							{concept.name}: <span className="feedback__number">{percent(concept.before)}%</span> →{' '}
							<span className="feedback__number feedback__number--now">{percent(concept.after)}%</span>
							{' · '}
							<LevelWord level={concept.level} band={concept.band} mastered={concept.mastered} />
						</p>
						<p className="feedback__update">{feedback.update}</p>
						<ProgressBar
							name={concept.name}
							before={concept.before}
							after={concept.after}
							unlock={feedback.thresholds.unlock}
							mastery={feedback.thresholds.mastery}
						/>
					</section>
				)}
			</div>
			<button type="button" className="feedback__continue" onClick={onContinue}>
				Back to the match
			</button>
		</section>
	)
}

/** With exact optional types, a missing unit is left out rather than passed as undefined. */
const unitOf = (unit: string | undefined) => (unit === undefined ? {} : { unit })

export default Feedback
