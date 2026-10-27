import { useEffect, useState } from 'react'

/** The reduced-motion media query, where the browser has one (jsdom hasn't). */
const motionQuery = (): MediaQueryList | undefined => {
	const { matchMedia } = window as { matchMedia?: Window['matchMedia'] }
	return matchMedia === undefined ? undefined : matchMedia.call(window, '(prefers-reduced-motion: reduce)')
}

/** True while the viewer prefers reduced motion; follows the setting if it changes. */
const useReducedMotion = () => {
	const [reduced, setReduced] = useState(() => motionQuery()?.matches ?? false)
	useEffect(() => {
		const query = motionQuery()
		if (query === undefined) return
		const follow = () => {
			setReduced(query.matches)
		}
		query.addEventListener('change', follow)
		return () => {
			query.removeEventListener('change', follow)
		}
	}, [])
	return reduced
}

export default useReducedMotion
