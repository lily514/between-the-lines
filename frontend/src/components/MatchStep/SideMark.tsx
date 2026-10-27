import type { Side } from './Commentary.support.ts'
import './SideMark.css'

/** A team's mark, as on the pitch: a filled disc for home, a ring for away. Its code or name is always beside it. */
const SideMark = ({ side }: { side: Side }) => <span className={`side-mark side-mark--${side}`} aria-hidden="true" />

export default SideMark
