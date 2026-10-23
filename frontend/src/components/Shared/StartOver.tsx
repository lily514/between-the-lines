import { useEffect, useRef, useState } from 'react'
import './StartOver.css'

export interface StartOverProps {
	/** The button's words before asking. */
	label?: string
	onConfirm: () => void
}

/** Starts a new viewer in this browser, after asking: the old viewer's id is forgotten, so their progress can't be
 * found again. */
const StartOver = ({ label = 'Start over', onConfirm }: StartOverProps) => {
	const [asking, setAsking] = useState(false)
	const keep = useRef<HTMLButtonElement>(null)

	useEffect(() => {
		if (asking) keep.current?.focus()
	}, [asking])

	if (!asking) {
		return (
			<button
				type="button"
				className="text-button"
				onClick={() => {
					setAsking(true)
				}}>
				{label}
			</button>
		)
	}
	return (
		<div className="start-over" role="group" aria-label="Start over?">
			<p className="start-over__question">Start over? Your progress here can’t be found again.</p>
			<button type="button" className="text-button" onClick={onConfirm}>
				Yes, start over
			</button>
			<button
				ref={keep}
				type="button"
				className="text-button"
				onClick={() => {
					setAsking(false)
				}}>
				Keep going
			</button>
		</div>
	)
}

export default StartOver
