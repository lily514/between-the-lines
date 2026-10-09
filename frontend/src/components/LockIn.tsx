import './LockIn.css'

export interface LockInProps {
	/** The picked option's key, or null before a pick. */
	selected: string | null
	/** True while the answer is being sent. */
	busy?: boolean
	onLockIn: (key: string) => void
}

/** Commits the pick. Before a pick it stays focusable but says what to do, rather than disappearing. */
const LockIn = ({ selected, busy = false, onLockIn }: LockInProps) => {
	const ready = selected !== null && !busy
	const text = busy ? 'Locking in…' : selected === null ? 'Pick an answer to lock in' : `Lock in ${selected}`
	return (
		<button
			type="button"
			className={`lock-in${ready ? ' lock-in--ready' : ''}${busy ? ' lock-in--busy' : ''}`}
			aria-disabled={!ready}
			onClick={() => {
				if (ready) {
					onLockIn(selected)
				}
			}}>
			{text}
		</button>
	)
}

export default LockIn
