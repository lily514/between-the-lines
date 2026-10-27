import { useEffect, useId, useRef, type ReactNode } from 'react'
import './index.css'

export interface StoryStepProps {
	/** The flow this step is part of, such as "Before match 2"; the welcome has none. */
	flow?: string
	/** This step's place in the flow, from 0. */
	index: number
	count: number
	/** Jump to the flow's last step; offered on every step but the last. */
	onSkip?: () => void
	onBack?: () => void
	next: { label: string; onClick: () => void }
	/** The scene card, drawn above the title. */
	scene?: ReactNode
	/** A small label over the title: the strand, or strand · concept. */
	eyebrow?: string
	title: string
	children: ReactNode
}

/**
 * One step of a story flow (B1 to B4): the flow label and counter over one segment per step, the scene, the title
 * and whatever the step says, then Back and Next. The title takes focus when the step changes.
 */
const StoryStep = ({ flow, index, count, onSkip, onBack, next, scene, eyebrow, title, children }: StoryStepProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const last = index >= count - 1

	useEffect(() => {
		heading.current?.focus()
	}, [index])

	return (
		<section className="story-step" aria-labelledby={headingId}>
			<div className="story-step__top">
				<span className="story-step__flow">{flow}</span>
				<span className="story-step__counter">
					{index + 1} of {count}
				</span>
				{!last && onSkip !== undefined && (
					<button type="button" className="text-button story-step__skip" onClick={onSkip}>
						Skip
					</button>
				)}
			</div>
			<div className="story-step__segments" aria-hidden="true">
				{Array.from({ length: count }, (_, i) => (
					<span
						key={i}
						className={i <= index ? 'story-step__segment story-step__segment--done' : 'story-step__segment'}
					/>
				))}
			</div>
			<div key={index} className="story-step__body">
				{scene}
				{eyebrow !== undefined && <p className="story-step__eyebrow">{eyebrow}</p>}
				<h2 id={headingId} ref={heading} tabIndex={-1} className="story-step__title screen-heading">
					{title}
				</h2>
				{children}
			</div>
			<div className="story-step__actions">
				{onBack !== undefined && (
					<button type="button" className="text-button story-step__back" onClick={onBack}>
						Back
					</button>
				)}
				<button type="button" className="primary-button story-step__next" onClick={next.onClick}>
					{next.label}
				</button>
			</div>
		</section>
	)
}

export default StoryStep
