import { useState } from 'react'
import type { BeforeMatch as BeforeMatchData } from '../../api/client.ts'
import type { BeforeFlow } from '../App.support.ts'
import LevelIcon from '../Shared/LevelIcon.tsx'
import LevelWord from '../Shared/LevelWord.tsx'
import { percent } from '../Shared/ProgressBar.support.ts'
import ExampleCard from '../Shared/StoryStep/ExampleCard.tsx'
import SceneCard from '../Shared/StoryStep/SceneCard.tsx'
import StoryStep from '../Shared/StoryStep/index.tsx'
import { exampleLabel, flowLabel, isNew, stepsOf, summaryOf } from './index.support.ts'
import './index.css'

export interface BeforeMatchProps {
	before: BeforeMatchData
	flow: BeforeFlow
	/** Open the curriculum map. */
	onMap: () => void
	/** The flow is finished: on to the next one, or to Who's playing. */
	onDone: () => void
}

/**
 * The flows before a match: a First look (B4) at each concept new to the viewer, or a Level-up (B2, B3) for each
 * concept whose level rose over their last match. Each is a step with the concept's scene at the level, then a
 * summary with every level, what the team sheet newly shows, and the way on to Who's playing.
 */
const BeforeMatch = ({ before, flow, onMap, onDone }: BeforeMatchProps) => {
	const steps = stepsOf(before, flow)
	const [index, setIndex] = useState(0)
	const count = steps.length + 1
	const step = steps[index]
	const flowName = flowLabel(before, flow)
	const back =
		index > 0
			? {
					onBack: () => {
						setIndex(index - 1)
					}
				}
			: {}

	if (step !== undefined) {
		return (
			<StoryStep
				flow={flowName}
				index={index}
				count={count}
				onSkip={() => {
					setIndex(steps.length)
				}}
				{...back}
				next={{
					label: 'Next',
					onClick: () => {
						setIndex(index + 1)
					}
				}}
				scene={
					<SceneCard
						concept={step.key}
						band={step.band}
						tag={{ text: step.tag, band: step.before === null ? null : step.band }}
					/>
				}
				eyebrow={`${step.strandName} · ${step.name}`}
				title={step.title}>
				<p className="before-match__learner">
					{step.before === null ? (
						<>
							<LevelIcon band={step.band} />
							Everyone starts at {step.level}
						</>
					) : (
						<>
							<span className="before-match__number">{percent(step.before)}%</span> →{' '}
							<span className="before-match__number">{percent(step.after)}%</span>
							<LevelIcon band={step.band} />
							Now {step.level}
						</>
					)}
				</p>
				<p className="story-step__text">{step.body}</p>
				<ExampleCard label={exampleLabel(step)} prompt={step.example} />
			</StoryStep>
		)
	}

	const summary = summaryOf(before, flow)
	return (
		<StoryStep
			flow={flowName}
			index={index}
			count={count}
			{...back}
			next={{ label: 'On to Who’s playing', onClick: onDone }}
			title={summary.title}>
			<p className="story-step__text">{summary.body}</p>
			<ul className="before-match__levels" aria-label="Your levels">
				{before.levels.map(row => (
					<li key={row.key} className="before-match__row">
						<span className="before-match__name">
							{row.name}
							{isNew(row, before, flow) && <span className="before-match__new">New</span>}
						</span>
						<LevelWord level={row.level} band={row.band} mastered={row.mastered} waitsFor={row.waits_for} />
						<span className="visually-hidden">{percent(row.mastery)}%</span>
					</li>
				))}
			</ul>
			{before.unlock_note !== null && (
				<p className="before-match__unlock">
					<svg className="before-match__unlock-icon" viewBox="0 0 20 20" aria-hidden="true">
						<rect x="3" y="3" width="14" height="14" rx="3" />
						<path d="M10 6.5 V13.5 M6.5 10 H13.5" />
					</svg>
					<span>{before.unlock_note}</span>
				</p>
			)}
			<button type="button" className="text-button before-match__map" onClick={onMap}>
				See your full map
			</button>
		</StoryStep>
	)
}

export default BeforeMatch
