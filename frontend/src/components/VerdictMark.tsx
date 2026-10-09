import './VerdictMark.css'

export type VerdictKind = 'correct' | 'incorrect' | 'mix-up'

const WORDS: Record<VerdictKind, string> = {
	correct: 'Right',
	incorrect: 'Not this one',
	'mix-up': 'Common mix-up'
}

export interface VerdictMarkProps {
	kind: VerdictKind
}

/** The verdict's mark: a filled circle with ✓ when right, a dashed circle with ✕ when not, ⚠ for a common mix-up.
 * Each is a different shape and carries its word for screen readers, so colour is never the only signal. */
const VerdictMark = ({ kind }: VerdictMarkProps) => (
	<svg className={`verdict-mark verdict-mark--${kind}`} viewBox="0 0 36 36" role="img" aria-label={WORDS[kind]}>
		{kind === 'correct' && (
			<>
				<circle className="verdict-mark__disc" cx="18" cy="18" r="17" />
				<path className="verdict-mark__glyph" d="M10.5 18.5l5 5 10-11" />
			</>
		)}
		{kind === 'incorrect' && (
			<>
				<circle className="verdict-mark__ring" cx="18" cy="18" r="16" />
				<path className="verdict-mark__glyph" d="M12.5 12.5l11 11M23.5 12.5l-11 11" />
			</>
		)}
		{kind === 'mix-up' && (
			<>
				<path className="verdict-mark__triangle" d="M18 5L32 30H4z" />
				<path className="verdict-mark__glyph" d="M18 14v7M18 25.5v.5" />
			</>
		)}
	</svg>
)

export default VerdictMark
