import type { Status } from '../../api/client.ts'

export type Pace = Status['pace']
export type Theme = 'system' | 'dark' | 'light'

export const PACES: { value: Pace; label: string }[] = [
	{ value: 'off', label: 'Off' },
	{ value: 'rarely', label: 'Rarely' },
	{ value: 'normal', label: 'Normal' }
]

export const THEMES: { value: Theme; label: string }[] = [
	{ value: 'system', label: 'Match device' },
	{ value: 'dark', label: 'Dark' },
	{ value: 'light', label: 'Light' }
]

const THEME_KEY = 'btl.theme'

// The theme is kept in this browser only. Storage can be missing or blocked; the page then follows the device.
export const rememberedTheme = (): Theme => {
	try {
		const kept = localStorage.getItem(THEME_KEY)
		return kept === 'dark' || kept === 'light' ? kept : 'system'
	} catch {
		return 'system'
	}
}

export const rememberTheme = (theme: Theme) => {
	try {
		if (theme === 'system') localStorage.removeItem(THEME_KEY)
		else localStorage.setItem(THEME_KEY, theme)
	} catch {
		// Not remembered: the next visit follows the device.
	}
}

/** Puts the theme on the page: tokens.css reads `data-theme`, and without it follows the device. */
export const applyTheme = (theme: Theme) => {
	if (theme === 'system') delete document.documentElement.dataset.theme
	else document.documentElement.dataset.theme = theme
}
