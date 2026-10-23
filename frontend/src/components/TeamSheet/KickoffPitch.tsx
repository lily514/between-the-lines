import type { KeyboardEvent } from 'react'
import type { TeamSheet } from '../../api/client.ts'
import { FULL_VIEW, MARKINGS, PITCH_LENGTH, PITCH_WIDTH, viewBoxText } from '../Shared/Pitch/index.support.ts'
import './KickoffPitch.css'
import { describeKickoff, halfLabel, labelBox, pitchLabel, spotLabel, type Spot } from './index.support.ts'

export interface KickoffPitchProps {
	sheet: TeamSheet
	spots: readonly Spot[]
	chosen: Spot | undefined
	/** From stage 2, the chosen player's label adds their position tag. */
	abbreviated: boolean
	onChoose: (key: string) => void
}

// The viewer's half, just inside the lines, and the "YOU" tag in its corner.
const YOUR_HALF = { x: 1, y: PITCH_LENGTH / 2 + 1.1, width: PITCH_WIDTH - 2, height: PITCH_LENGTH / 2 - 2.1 }
const YOU_TAG = { width: 18.5, height: 4.6 }

/** Both elevens at kick-off, the first team attacking up. Each player is a button that fills the player card. */
const KickoffPitch = ({ sheet, spots, chosen, abbreviated, onChoose }: KickoffPitchProps) => {
	const [up, down] = sheet.teams
	const label = chosen === undefined ? null : pitchLabel(chosen, abbreviated)
	const box = chosen === undefined || label === null ? null : labelBox(chosen.at, label)
	const onKey = (key: string) => (event: KeyboardEvent) => {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault()
			onChoose(key)
		}
	}
	return (
		<svg
			className="kickoff-pitch"
			viewBox={viewBoxText(FULL_VIEW)}
			role="group"
			aria-label={describeKickoff(sheet)}>
			<rect
				className="kickoff-pitch__grass"
				x={FULL_VIEW.x}
				y={FULL_VIEW.y}
				width={FULL_VIEW.width}
				height={FULL_VIEW.height}
			/>
			<g className="kickoff-pitch__markings">
				<rect {...MARKINGS.outline} />
				<line x1={0} y1={MARKINGS.halfway} x2={MARKINGS.outline.width} y2={MARKINGS.halfway} />
				<circle cx={MARKINGS.centre.x} cy={MARKINGS.centre.y} r={MARKINGS.centre.r} />
				{MARKINGS.boxes.map(b => (
					<rect key={`${String(b.y)}-${String(b.width)}`} {...b} />
				))}
			</g>
			{up?.yours === true && (
				<g aria-hidden="true">
					<rect className="kickoff-pitch__your-half" data-testid="your-half" rx={2.5} {...YOUR_HALF} />
					<rect
						className="kickoff-pitch__you-tag"
						x={YOUR_HALF.x + YOUR_HALF.width - YOU_TAG.width - 0.5}
						y={YOUR_HALF.y + YOUR_HALF.height - YOU_TAG.height - 0.4}
						rx={1}
						{...YOU_TAG}
					/>
					<text
						className="kickoff-pitch__you-text"
						x={YOUR_HALF.x + YOUR_HALF.width - YOU_TAG.width / 2 - 0.5}
						y={YOUR_HALF.y + YOUR_HALF.height - 1.3}>
						YOU · {up.code}
					</text>
				</g>
			)}
			<g className="kickoff-pitch__half-names" aria-hidden="true">
				{down !== undefined && (
					<text x={1.5} y={-0.6}>
						{halfLabel(down)}
					</text>
				)}
				{up !== undefined && (
					<text x={1.5} y={PITCH_LENGTH + 2.6}>
						{halfLabel(up)}
					</text>
				)}
			</g>
			{spots.map(spot => {
				const [x, y] = spot.at
				const shape = spot.team.home ? 'home' : 'away'
				const picked = spot.key === chosen?.key
				return (
					<g
						key={spot.key}
						role="button"
						tabIndex={0}
						className={`kickoff-pitch__player kickoff-pitch__player--${shape}${picked ? ' kickoff-pitch__player--chosen' : ''}`}
						aria-label={spotLabel(spot)}
						aria-pressed={picked}
						data-testid={`pitch-${spot.key}`}
						onClick={() => {
							onChoose(spot.key)
						}}
						onFocus={() => {
							onChoose(spot.key)
						}}
						onMouseEnter={() => {
							onChoose(spot.key)
						}}
						onKeyDown={onKey(spot.key)}>
						<circle className="kickoff-pitch__hit" cx={x} cy={y} r={4} />
						<circle className="kickoff-pitch__focus" cx={x} cy={y} r={4.3} />
						<circle className="kickoff-pitch__ring" cx={x} cy={y} r={3.5} />
						<circle className="kickoff-pitch__disc" cx={x} cy={y} r={spot.team.home ? 2.4 : 2.3} />
						<text className="kickoff-pitch__number" x={x} y={y + 0.8}>
							{spot.player.shirt}
						</text>
					</g>
				)
			})}
			{box !== null && label !== null && (
				<g className="kickoff-pitch__label" aria-hidden="true">
					<rect rx={1.2} {...box} />
					<text x={box.x + box.width / 2} y={box.y + 3.5}>
						{label}
					</text>
				</g>
			)}
		</svg>
	)
}

export default KickoffPitch
