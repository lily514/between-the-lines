import type { CSSProperties } from 'react'
import './ProgressBar.css'
import { barParts, barText, percent } from './ProgressBar.support.ts'

export interface ProgressBarProps {
	/** The concept's name, read before the bar. */
	name: string
	before: number
	after: number
	unlock: number
	mastery: number
}

/** How sure the learner model is about one concept: the part already known, this answer's gain (or the stretch lost),
 * and ticks where the next concept unlocks (solid) and where it counts as mastered (dashed). */
const ProgressBar = ({ name, before, after, unlock, mastery }: ProgressBarProps) => {
	const parts = barParts(before, after)
	const width = (share: number): CSSProperties => ({ width: `${String(share)}%` })
	const at = (share: number): CSSProperties => ({ left: `${String(percent(share))}%` })
	return (
		<div className="progress-bar">
			<div
				className="progress-bar__track"
				role="meter"
				aria-label={name}
				aria-valuemin={0}
				aria-valuemax={100}
				aria-valuenow={percent(after)}
				aria-valuetext={barText(before, after, unlock, mastery)}>
				<span className="progress-bar__kept" style={width(parts.kept)} />
				{parts.gained > 0 && <span className="progress-bar__gained" style={width(parts.gained)} />}
				{parts.lost > 0 && <span className="progress-bar__lost" style={width(parts.lost)} />}
				<span className="progress-bar__tick progress-bar__tick--unlock" style={at(unlock)} />
				<span className="progress-bar__tick progress-bar__tick--mastery" style={at(mastery)} />
			</div>
			<p className="progress-bar__legend" aria-hidden="true">
				<span>
					<span className="progress-bar__key progress-bar__key--unlock" />
					{percent(unlock)} unlocks next
				</span>
				<span>
					<span className="progress-bar__key progress-bar__key--mastery" />
					{percent(mastery)} mastered
				</span>
			</p>
		</div>
	)
}

export default ProgressBar
