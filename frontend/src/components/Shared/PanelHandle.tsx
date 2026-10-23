import { useState, type KeyboardEvent, type PointerEvent } from 'react'
import './PanelHandle.css'
import { clampPanelWidth, PANEL_MIN, PANEL_STEP, panelMax } from './PanelHandle.support.ts'

export interface PanelHandleProps {
	/** The panel's width in pixels. */
	width: number
	onResize: (width: number) => void
	/** Back to the usual width (double-click). */
	onReset: () => void
	/** A drag has finished or a key was pressed: the width to keep and remember. */
	onSettle: (width: number) => void
}

/** The panel's left edge on a wide screen: drag it, or focus it and use the arrow keys, to make the panel wider or
 * narrower. The panel sits on the right, so its width is the distance from the pointer to the window's right edge. */
const PanelHandle = ({ width, onResize, onReset, onSettle }: PanelHandleProps) => {
	const [dragging, setDragging] = useState(false)
	const fit = (to: number) => clampPanelWidth(to, window.innerWidth)

	const start = (event: PointerEvent<HTMLDivElement>) => {
		if (event.button !== 0) return
		event.preventDefault()
		event.currentTarget.setPointerCapture(event.pointerId)
		setDragging(true)
	}

	const move = (event: PointerEvent<HTMLDivElement>) => {
		if (dragging) onResize(fit(window.innerWidth - event.clientX))
	}

	const stop = (event: PointerEvent<HTMLDivElement>) => {
		if (!dragging) return
		event.currentTarget.releasePointerCapture(event.pointerId)
		setDragging(false)
		onSettle(fit(window.innerWidth - event.clientX))
	}

	const key = (event: KeyboardEvent<HTMLDivElement>) => {
		const to =
			event.key === 'ArrowLeft'
				? width + PANEL_STEP
				: event.key === 'ArrowRight'
					? width - PANEL_STEP
					: event.key === 'Home'
						? PANEL_MIN
						: event.key === 'End'
							? panelMax(window.innerWidth)
							: null
		if (to === null) return
		event.preventDefault()
		onSettle(fit(to))
	}

	return (
		<div
			className={`panel-handle${dragging ? ' panel-handle--dragging' : ''}`}
			role="separator"
			aria-orientation="vertical"
			aria-label="Panel width"
			aria-valuemin={PANEL_MIN}
			aria-valuemax={panelMax(window.innerWidth)}
			aria-valuenow={width}
			title="Drag to resize the panel · double-click to reset"
			tabIndex={0}
			onPointerDown={start}
			onPointerMove={move}
			onPointerUp={stop}
			onPointerCancel={stop}
			onKeyDown={key}
			onDoubleClick={onReset}
		/>
	)
}

export default PanelHandle
