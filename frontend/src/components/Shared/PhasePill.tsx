import './PhasePill.css'
import { pillKind, pillText, type PillKind } from './PhasePill.support.ts'

export interface PhasePillProps {
	/** A phase of play as the API sends it ("settled", "dead ball", …), or "your read" for a live question. */
	phase: string
	/** Shown after the phase, such as the restart: "Dead ball · free kick". */
	detail?: string | null
}

/** Where play is, as an icon and words. A live question's pill is filled with the action colour. */
const PhasePill = ({ phase, detail }: PhasePillProps) => {
	const kind = pillKind(phase)
	return (
		<span className={`phase-pill${kind === 'your read' ? ' phase-pill--act' : ''}`}>
			{kind !== undefined && <PhaseIcon kind={kind} />}
			{pillText(phase, detail)}
		</span>
	)
}

const PhaseIcon = ({ kind }: { kind: PillKind }) => (
	<svg className="phase-pill__icon" viewBox="0 0 24 24" aria-hidden="true">
		{kind === 'settled' && <path d="M3 12h4l3-5 4 10 3-5h4" />}
		{kind === 'transition' && <path d="M4 8h14l-3-3M20 16H6l3 3" />}
		{kind === 'dead ball' && <rect x="5" y="5" width="14" height="14" rx="2" />}
		{kind === 'half-time' && <path d="M9 5v14M15 5v14" />}
		{kind === 'full time' && <path d="M5 21V4h10l-1.5 3.5L15 11H5" />}
		{kind === 'your read' && <path d="M9 5v14M15 5v14" />}
	</svg>
)

export default PhasePill
