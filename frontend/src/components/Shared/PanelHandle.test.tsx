import { fireEvent, render, screen } from '@testing-library/react'
import PanelHandle from './PanelHandle.tsx'
import {
	clampPanelWidth,
	PANEL_MIN,
	rememberedPanelWidth,
	rememberPanelWidth,
	STREAM_MIN
} from './PanelHandle.support.ts'

beforeEach(() => {
	localStorage.clear()
	window.innerWidth = 1400
})

const renderHandle = (width = 420) => {
	const onResize = vi.fn()
	const onSettle = vi.fn()
	const onReset = vi.fn()
	render(<PanelHandle width={width} onResize={onResize} onSettle={onSettle} onReset={onReset} />)
	return { onResize, onSettle, onReset, handle: screen.getByRole('separator', { name: 'Panel width' }) }
}

test('the panel never gets narrower than its minimum or leaves the stream area too little room', () => {
	expect(clampPanelWidth(200, 1400)).toBe(PANEL_MIN)
	expect(clampPanelWidth(700.4, 1400)).toBe(700)
	expect(clampPanelWidth(1300, 1400)).toBe(1400 - STREAM_MIN)
})

test('the width is remembered, and forgotten on reset', () => {
	expect(rememberedPanelWidth()).toBeNull()
	rememberPanelWidth(640)
	expect(rememberedPanelWidth()).toBe(640)
	rememberPanelWidth(null)
	expect(rememberedPanelWidth()).toBeNull()
})

test('a remembered width that makes no sense is ignored', () => {
	localStorage.setItem('btl.panel-width', 'wide')
	expect(rememberedPanelWidth()).toBeNull()
})

test('the arrow keys make the panel wider or narrower, Home and End go to the limits', () => {
	const { handle, onSettle } = renderHandle(500)
	fireEvent.keyDown(handle, { key: 'ArrowLeft' })
	expect(onSettle).toHaveBeenLastCalledWith(520)
	fireEvent.keyDown(handle, { key: 'ArrowRight' })
	expect(onSettle).toHaveBeenLastCalledWith(480)
	fireEvent.keyDown(handle, { key: 'Home' })
	expect(onSettle).toHaveBeenLastCalledWith(PANEL_MIN)
	fireEvent.keyDown(handle, { key: 'End' })
	expect(onSettle).toHaveBeenLastCalledWith(1400 - STREAM_MIN)
})

test('the handle tells a screen reader how wide the panel is', () => {
	const { handle } = renderHandle(520)
	expect(handle).toHaveAttribute('aria-valuenow', '520')
	expect(handle).toHaveAttribute('aria-valuemax', String(1400 - STREAM_MIN))
})

test('double-clicking the handle puts the panel back to its usual width', () => {
	const { handle, onReset } = renderHandle(600)
	fireEvent.doubleClick(handle)
	expect(onReset).toHaveBeenCalled()
})
