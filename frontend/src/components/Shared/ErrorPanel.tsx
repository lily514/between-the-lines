import { useEffect, useId, useRef } from 'react'
import './ErrorPanel.css'

export interface ErrorPanelProps {
	message: string
	onRetry: () => void
}

/** A request failed: say so plainly and offer to try again. Nothing the viewer did is lost by retrying. */
const ErrorPanel = ({ message, onRetry }: ErrorPanelProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="error-panel" aria-labelledby={headingId} role="alert">
			<h2 id={headingId} ref={heading} tabIndex={-1} className="error-panel__heading screen-heading">
				That didn’t come through
			</h2>
			<p className="error-panel__message">{message}</p>
			<button type="button" className="primary-button" onClick={onRetry}>
				Try again
			</button>
		</section>
	)
}

export default ErrorPanel
