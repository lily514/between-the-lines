import { useId } from 'react'
import type { Picture } from '../../../api/client.ts'
import './index.css'
import {
	FULL_VIEW,
	MARKINGS,
	ballOnScreen,
	carrierOf,
	cropTo,
	describePitch,
	isInvolved,
	momentPoints,
	pathData,
	startsAtBall,
	tagPosition,
	toScreen,
	viewBoxText,
	type PitchOption,
	type Point
} from './index.support.ts'

export interface PitchProps {
	picture: Picture
	/** Where the viewer could say it goes; each gets a dashed arrow from the ball and its letter. */
	options?: readonly PitchOption[]
	/** The play's real path, in picture coordinates. */
	path?: readonly Point[]
	/** Draw the path as a reveal: traced over 600 ms, or faded in when motion is reduced. */
	reveal?: boolean
	/** `moment` crops top and bottom to the ball, options and path; `full` shows the whole pitch. */
	crop?: 'full' | 'moment'
	/** The start of what a screen reader hears, such as "Freeze-frame at 58:13". */
	label: string
}

/** The pitch as an SVG in metres, portrait, with the team on the ball attacking up. */
const Pitch = ({ picture, options = [], path = [], reveal = false, crop = 'full', label }: PitchProps) => {
	const arrowId = useId()
	const view = crop === 'moment' ? cropTo(momentPoints(picture, options, path)) : FULL_VIEW
	const ball = ballOnScreen(picture)
	const carrier = carrierOf(picture)
	// Lines start at the ball as drawn, beside the carrier, so they never cross the shirt number.
	const from = ball
	const focused = options.length > 0 || path.length > 0
	const playerPoints = picture.markers.map(m => toScreen([m.x, m.y]))
	// Involved players on top of dimmed ones, and within each, home discs over away rings so numbers stay readable.
	const layer = (m: Picture['markers'][number]) => Number(isInvolved(m, options, path)) * 2 + Number(m.home)
	const players = [...picture.markers].sort((a, b) => layer(a) - layer(b))
	return (
		<svg
			className="pitch"
			viewBox={viewBoxText(view)}
			role="img"
			aria-label={describePitch(label, picture, options)}>
			<defs>
				<marker
					id={arrowId}
					viewBox="0 0 6 6"
					refX="5"
					refY="3"
					markerWidth="3.6"
					markerHeight="3.6"
					orient="auto">
					<path className="pitch__arrowhead" d="M0 0L6 3L0 6z" />
				</marker>
			</defs>
			<rect
				className="pitch__grass"
				x={FULL_VIEW.x}
				y={FULL_VIEW.y}
				width={FULL_VIEW.width}
				height={FULL_VIEW.height}
			/>
			<g className="pitch__markings">
				<rect {...MARKINGS.outline} />
				<line x1={0} y1={MARKINGS.halfway} x2={MARKINGS.outline.width} y2={MARKINGS.halfway} />
				<circle cx={MARKINGS.centre.x} cy={MARKINGS.centre.y} r={MARKINGS.centre.r} />
				{MARKINGS.boxes.map(box => (
					<rect key={`${String(box.y)}-${String(box.width)}`} {...box} />
				))}
				{MARKINGS.spots.map(([x, y]) => (
					<circle key={y} className="pitch__spot" cx={x} cy={y} r={0.3} />
				))}
			</g>
			{options.length > 0 && (
				<g className="pitch__options" data-testid="pitch-options">
					{options.map(option => (
						<path
							key={option.key}
							className="pitch__option-line"
							d={pathData([from, toScreen(option.at)])}
							markerEnd={`url(#${arrowId})`}
						/>
					))}
				</g>
			)}
			{carrier !== undefined && focused && (
				<circle
					className="pitch__halo"
					cx={toScreen([carrier.x, carrier.y])[0]}
					cy={toScreen([carrier.x, carrier.y])[1]}
					r={3.8}
				/>
			)}
			<g className="pitch__players">
				{players.map(marker => {
					const [x, y] = toScreen([marker.x, marker.y])
					const dim = focused && !isInvolved(marker, options, path)
					const shape = marker.home ? 'home' : 'away'
					return (
						<g
							key={`${shape}-${String(marker.shirt)}`}
							className={`pitch__player pitch__player--${shape}${dim ? ' pitch__player--dim' : ''}`}
							data-testid={`player-${shape}`}>
							{marker.home ? (
								<>
									<circle cx={x} cy={y} r={2.2} />
									<text x={x} y={y + 0.85}>
										{marker.shirt}
									</text>
								</>
							) : (
								<circle cx={x} cy={y} r={1.8} />
							)}
						</g>
					)
				})}
			</g>
			{path.length > 1 && (
				<path
					className={`pitch__path${reveal ? ' pitch__path--reveal' : ''}`}
					data-testid="pitch-path"
					d={pathData(
						path.map((point, i) => (i === 0 && startsAtBall(point, picture) ? ball : toScreen(point)))
					)}
					pathLength={1}
					markerEnd={`url(#${arrowId})`}
				/>
			)}
			<circle className="pitch__ball" cx={ball[0]} cy={ball[1]} r={0.95} />
			{options.map(option => {
				const [x, y] = tagPosition(from, toScreen(option.at), playerPoints)
				return (
					<g key={option.key} className="pitch__tag" aria-hidden="true">
						<circle cx={x} cy={y} r={2.4} />
						<text x={x} y={y + 0.95}>
							{option.key}
						</text>
					</g>
				)
			})}
		</svg>
	)
}

export default Pitch
