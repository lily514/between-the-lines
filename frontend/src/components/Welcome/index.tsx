import { useState } from 'react'
import type { ConceptMap } from '../../api/client.ts'
import LevelIcon from '../Shared/LevelIcon.tsx'
import ExampleCard from '../Shared/StoryStep/ExampleCard.tsx'
import SceneCard from '../Shared/StoryStep/SceneCard.tsx'
import StoryStep from '../Shared/StoryStep/index.tsx'
import Intro from './Intro.tsx'
import { summaryRows, welcomeSteps } from './index.support.ts'
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

/** Where the welcome starts: the intro page, before the counted steps. */
const INTRO = -1

const LEVELS = [
	{ band: 'getting_there', word: 'Getting there', note: ' (you start here)' },
	{ band: 'solid', word: 'Solid', note: '' },
	{ band: 'sharp', word: 'Sharp', note: '' }
] as const

/**
 * The first screen (B1): an intro to what the app is, then a step per strand with something asked about now, each
 * with its scene at Getting there, then a summary of what the questions cover and where everyone starts. Continue goes
 * on to the club picker.
 *
 * There is no sign-in: the page makes the viewer a random id and keeps it in this browser. A viewer sent back here
 * with an error has seen the intro and the steps, so they land on the summary.
 */
const Welcome = ({ curriculum, error, onStart, onSeeAll }: WelcomeProps) => {
	const steps = curriculum === null ? [] : welcomeSteps(curriculum)
	const [chosen, setChosen] = useState(error === null ? INTRO : Infinity)
	const index = Math.min(chosen, steps.length)
	const count = steps.length + 1
	const step = steps[index]
	const rows = curriculum === null ? [] : summaryRows(curriculum)
	const back = {
		onBack: () => {
			setChosen(index - 1)
		}
	}

	if (index === INTRO) {
		return (
			<Intro
				onNext={() => {
					setChosen(0)
				}}
				onSkip={() => {
					setChosen(Infinity)
				}}
			/>
		)
	}

	if (step !== undefined) {
		return (
			<StoryStep
				index={index}
				count={count}
				onSkip={() => {
					setChosen(Infinity)
				}}
				{...back}
				next={{
					label: 'Next',
					onClick: () => {
						setChosen(index + 1)
					}
				}}
				scene={<SceneCard concept={step.scene} band="getting_there" />}
				eyebrow={step.name}
				title={step.copy.title}>
				<p className="story-step__text">{step.copy.body}</p>
				<p className="story-step__line">{step.concepts.map(concept => concept.name).join(' · ')}</p>
				<ExampleCard label="You might get" prompt={step.example} />
			</StoryStep>
		)
	}

	return (
		<StoryStep
			index={index}
			count={count}
			{...back}
			next={{ label: 'Continue', onClick: onStart }}
			title="You guess first. Then we show you.">
			<p className="story-step__text">One question at a time, only when play allows. Turn them off any time.</p>
			{rows.length > 0 && (
				<ul className="welcome__rows" aria-label="What the questions cover">
					{rows.map(row => (
						<li key={row.name} className="welcome__row">
							<span className="welcome__row-name">{row.name}</span>
							<span
								className={
									row.later ? 'welcome__row-detail welcome__row-detail--later' : 'welcome__row-detail'
								}>
								{row.later && <LaterIcon />}
								{row.detail}
							</span>
						</li>
					))}
				</ul>
			)}
			<div className="welcome__levels">
				<span className="welcome__levels-label">Everyone starts here</span>
				<ol className="welcome__track" aria-label="Levels">
					{LEVELS.map((level, i) => (
						<li
							key={level.band}
							className={i === 0 ? 'welcome__level welcome__level--start' : 'welcome__level'}>
							{i > 0 && <span aria-hidden="true">→ </span>}
							<LevelIcon band={level.band} />
							{level.word}
							{level.note !== '' && <span className="visually-hidden">{level.note}</span>}
						</li>
					))}
				</ol>
			</div>
			<button type="button" className="text-button welcome__all" onClick={onSeeAll}>
				See all {curriculum === null ? '' : `${String(curriculum.concepts.length)} `}concepts
			</button>
			<p className="welcome__hint">No sign-in. This browser keeps your place.</p>
			{error !== null && (
				<p className="welcome__error" role="alert">
					{error}
				</p>
			)}
		</StoryStep>
	)
}

/** A small clock: a strand whose concepts are coming later. */
const LaterIcon = () => (
	<svg className="welcome__later-icon" viewBox="0 0 14 14" aria-hidden="true">
		<circle cx="7" cy="7" r="5.5" />
		<path d="M7 4 V7 L9 8.5" />
	</svg>
)

export default Welcome
