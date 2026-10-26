import type { ReactNode, Ref } from 'react'
import './Header.css'

export interface HeaderProps {
	/** Whether the map button shows: on every screen after the viewer has picked a team. */
	showMap: boolean
	/** Whether the map is open now, so the button reads as pressed. */
	mapOpen: boolean
	onMap: () => void
	/** The map button, so focus can come back to it when the map closes. */
	mapButton?: Ref<HTMLButtonElement>
	/** More header buttons, to the right of the map. */
	children?: ReactNode
}

/** The panel's header: the name, then the map button (and any others) on the right. */
const Header = ({ showMap, mapOpen, onMap, mapButton, children }: HeaderProps) => (
	<header className="header">
		<h1 className="header__name">
			Between <span className="header__the">the</span> Lines
		</h1>
		<div className="header__actions">
			{showMap && (
				<button
					ref={mapButton}
					type="button"
					className="icon-button"
					aria-label="Curriculum map"
					aria-pressed={mapOpen}
					onClick={onMap}>
					<MapIcon />
				</button>
			)}
			{children}
		</div>
	</header>
)

/** A pitch frame with two linked nodes: the map of what there is to learn. */
const MapIcon = () => (
	<svg className="icon-button__icon" viewBox="0 0 24 24" aria-hidden="true">
		<rect x="3" y="4" width="18" height="16" rx="2" />
		<path d="M3 12h18" />
		<circle cx="8.5" cy="8.5" r="1.8" />
		<circle cx="15.5" cy="15.5" r="1.8" />
		<path d="M9.8 9.8l4.4 4.4" />
	</svg>
)

export default Header
