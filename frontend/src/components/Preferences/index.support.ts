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

/** How many times faster than real time the match feed plays; 1 is real time. */
export type FeedSpeed = 1 | 20 | 40 | 80

/** How the match feed plays between questions. In demo mode no gap between questions takes longer than 20 s. */
export interface Playback {
	speed: FeedSpeed
	demo: boolean
}

export const FEED_SPEEDS: { value: FeedSpeed; label: string }[] = [
	{ value: 1, label: '1×' },
	{ value: 20, label: '20×' },
	{ value: 40, label: '40×' },
	{ value: 80, label: '80×' }
]

export const DEMO_OPTIONS: { value: boolean; label: string }[] = [
	{ value: true, label: 'On' },
	{ value: false, label: 'Off' }
]

export const DEFAULT_PLAYBACK: Playback = { speed: 40, demo: true }

const SPEED_KEY = 'btl.feedSpeed'
const DEMO_KEY = 'btl.demo'

// Kept in this browser only, like the theme; without storage the feed plays at 40× in demo mode.
export const rememberedPlayback = (): Playback => {
	try {
		const speed = Number(localStorage.getItem(SPEED_KEY))
		return {
			speed: FEED_SPEEDS.find(option => option.value === speed)?.value ?? DEFAULT_PLAYBACK.speed,
			demo: localStorage.getItem(DEMO_KEY) !== 'off'
		}
	} catch {
		return DEFAULT_PLAYBACK
	}
}

export const rememberPlayback = (playback: Playback) => {
	try {
		localStorage.setItem(SPEED_KEY, String(playback.speed))
		if (playback.demo) localStorage.removeItem(DEMO_KEY)
		else localStorage.setItem(DEMO_KEY, 'off')
	} catch {
		// Not remembered: the next visit plays at 40× in demo mode.
	}
}
