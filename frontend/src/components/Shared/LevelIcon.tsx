import type { Band } from '../../api/client.ts'
import './LevelIcon.css'

export interface LevelIconProps {
	band: Band
	/** Mastered draws a tick in a full disc instead of the band's fill. */
	mastered?: boolean
}

/** The mark beside every level word, so a level is never told by the word's colour alone: a quarter-filled circle for
 * Getting there, half for Solid, full for Sharp, and a tick for Mastered. Decorative: the word carries the meaning. */
const LevelIcon = ({ band, mastered = false }: LevelIconProps) => (
	<svg
		viewBox="0 0 12 12"
		className="level-icon"
		data-band={mastered ? 'mastered' : band}
		aria-hidden="true"
		focusable="false">
		{band === 'sharp' || mastered ? (
			<circle cx="6" cy="6" r="5.4" className="level-icon__fill" />
		) : (
			<>
				<circle cx="6" cy="6" r="4.8" className="level-icon__ring" />
				<path d={band === 'solid' ? HALF : QUARTER} className="level-icon__fill" />
			</>
		)}
		{mastered && <path d="M3.4 6.2l1.8 1.8 3.4-3.8" className="level-icon__tick" />}
	</svg>
)

const QUARTER = 'M6 6 V1.2 A4.8 4.8 0 0 1 10.8 6 Z'
const HALF = 'M6 1.2 A4.8 4.8 0 0 1 6 10.8 Z'

export default LevelIcon
