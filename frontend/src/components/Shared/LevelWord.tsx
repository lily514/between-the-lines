import type { Band } from '../../api/client.ts'
import LevelIcon from './LevelIcon.tsx'
import { unlocksAfter } from './LevelWord.support.ts'
import './LevelWord.css'

export interface LevelWordProps {
	/** The level word from the API: Getting there, Solid, Sharp or Mastered. */
	level: string
	band: Band
	mastered?: boolean
	/** The askable prerequisites the concept still waits for. While there are any, the row reads as locked. */
	waitsFor?: readonly string[]
}

/** A level word with its icon, or the locked state: "Unlocks after {prerequisite}", dashed, with no icon. */
const LevelWord = ({ level, band, mastered = false, waitsFor = [] }: LevelWordProps) => {
	if (waitsFor.length > 0 && !mastered) {
		return <span className="level-word level-word--locked">{unlocksAfter(waitsFor)}</span>
	}
	return (
		<span className="level-word">
			<LevelIcon band={band} mastered={mastered} />
			{level}
		</span>
	)
}

export default LevelWord
