import { useEffect, useId, useRef } from 'react'
import './Intro.css'

export interface IntroProps {
	/** Go on to the welcome's steps. */
	onNext: () => void
	/** Jump straight to the welcome's summary. */
	onSkip: () => void
}

const HOW = [
	{
		title: 'Follow a match',
		body: 'Pick a team to support and follow their matches here, moment by moment.'
	},
	{
		title: 'Answer when play stops',
		body: 'At a stoppage or a quiet spell, you get one quick question. Never in the middle of a fast break.'
	},
	{
		title: 'Guess first, then see',
		body: 'Say what you think, then we show you what happened and why.'
	},
	{
		title: 'Grow at your pace',
		body: 'Each topic moves up as you get it right, from Getting there to Solid to Sharp.'
	}
]

/** The very first page: what Between the Lines is and how it works, before the welcome's scenes. */
const Intro = ({ onNext, onSkip }: IntroProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="intro" aria-labelledby={headingId}>
			<IntroPitch />
			<p className="intro__eyebrow">Welcome to Between the Lines</p>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="intro__title screen-heading">
				From ‘what just happened?’ to ‘I saw that coming.’
			</h2>
			<p className="intro__lede">
				An adaptive learning tool for football fans at every level. It helps you read the game as it plays out.
			</p>
			<ol className="intro__how" aria-label="How it works">
				{HOW.map((item, i) => (
					<li key={item.title} className="intro__how-item">
						<span className="intro__how-number" aria-hidden="true">
							{i + 1}
						</span>
						<span className="intro__how-words">
							<span className="intro__how-title">{item.title}</span>
							<span className="intro__how-body">{item.body}</span>
						</span>
					</li>
				))}
			</ol>
			<div className="intro__actions">
				<button type="button" className="primary-button intro__next" onClick={onNext}>
					Show me what I’ll learn
				</button>
				<button type="button" className="text-button intro__skip" onClick={onSkip}>
					Skip the tour
				</button>
			</div>
			<p className="intro__hint">No sign-in. This browser keeps your place.</p>
		</section>
	)
}

/** A still pitch: two lines of defenders and a pass threading the gap between them. */
const IntroPitch = () => (
	<svg className="intro__pitch" viewBox="0 0 320 120" aria-hidden="true">
		<rect className="intro__pitch-grass" x="0" y="0" width="320" height="120" rx="10" />
		<path className="intro__pitch-line" d="M160 0 V120 M8 8 H312 V112 H8 Z" />
		<circle className="intro__pitch-line" cx="160" cy="60" r="18" />
		<path className="intro__pitch-line intro__pitch-gap" d="M150 14 V106 M210 14 V106" />
		{[22, 48, 74, 100].map(y => (
			<circle key={`a${String(y)}`} className="intro__pitch-away" cx="150" cy={y} r="6" />
		))}
		{[28, 60, 92].map(y => (
			<circle key={`b${String(y)}`} className="intro__pitch-away" cx="210" cy={y} r="6" />
		))}
		<circle className="intro__pitch-home" cx="96" cy="76" r="6" />
		<circle className="intro__pitch-home" cx="262" cy="46" r="6" />
		<path className="intro__pitch-pass" d="M104 74 Q180 64 254 48" />
		<circle className="intro__pitch-ball" cx="180" cy="62" r="4" />
	</svg>
)

export default Intro
