/** The side panel's width before the viewer drags it, as --panel-w in tokens.css. */
export const PANEL_DEFAULT = 420
/** Narrower than this and the answer tiles stop fitting three across. */
export const PANEL_MIN = 360
/** The stream area always keeps at least this much room, so the panel never covers the viewer's match. */
export const STREAM_MIN = 320
/** How far one arrow key press moves the handle. */
export const PANEL_STEP = 20

/** The widest the panel may be on a window this wide. */
export const panelMax = (viewport: number) => Math.max(PANEL_MIN, viewport - STREAM_MIN)

export const clampPanelWidth = (width: number, viewport: number) =>
	Math.round(Math.min(panelMax(viewport), Math.max(PANEL_MIN, width)))

const PANEL_KEY = 'btl.panel-width'

// Like the viewer's name, the width is remembered for this browser only, and the page works without it.
export const rememberedPanelWidth = (): number | null => {
	try {
		const width = Number(localStorage.getItem(PANEL_KEY))
		return width >= PANEL_MIN ? width : null
	} catch {
		return null
	}
}

export const rememberPanelWidth = (width: number | null) => {
	try {
		if (width === null) localStorage.removeItem(PANEL_KEY)
		else localStorage.setItem(PANEL_KEY, String(width))
	} catch {
		// Not remembered: the panel opens at its usual width next time.
	}
}
