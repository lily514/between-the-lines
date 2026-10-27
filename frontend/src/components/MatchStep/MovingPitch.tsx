import { FULL_VIEW, besideCarrier, toScreen, viewBoxText } from '../Shared/Pitch/index.support.ts'
import '../Shared/Pitch/index.css'
import Markings from '../Shared/Pitch/Markings.tsx'
import PlayerMark from '../Shared/Pitch/PlayerMark.tsx'
import useReducedMotion from '../Shared/useReducedMotion.ts'
import type { Side } from './Commentary.support.ts'
import { trackAt, type Track } from './MovingPitch.support.ts'

export interface MovingPitchProps {
	track: Track
	/** Seconds on the match clock. */
	at: number
	/** Which side is the viewer's team: its players get a dashed ring. */
	yours: Side | null
}

/** The whole pitch with the players and the ball where they are on the match clock, the viewer's team attacking up.
 * Hidden from screen readers: the commentary beside it says what is happening. Nothing when the track is empty. */
const MovingPitch = ({ track, at, yours }: MovingPitchProps) => {
	const reduced = useReducedMotion()
	const now = trackAt(track, at, !reduced)
	if (now === null) {
		return null
	}
	const carrier = now.players.find(player => player.onBall)
	const ball = besideCarrier(now.ball, carrier?.at)
	// Home discs over away rings, so the numbers stay readable.
	const players = [...now.players].sort((a, b) => Number(a.home) - Number(b.home))
	return (
		<svg className="pitch" viewBox={viewBoxText(FULL_VIEW)} aria-hidden="true" data-testid="moving-pitch">
			<rect
				className="pitch__grass"
				x={FULL_VIEW.x}
				y={FULL_VIEW.y}
				width={FULL_VIEW.width}
				height={FULL_VIEW.height}
			/>
			<Markings />
			{carrier !== undefined && (
				<circle
					className="pitch__halo"
					data-testid="moving-pitch-halo"
					cx={toScreen(carrier.at)[0]}
					cy={toScreen(carrier.at)[1]}
					r={3.8}
				/>
			)}
			<g className="pitch__players">
				{players.map(player => (
					<PlayerMark
						key={`${player.home ? 'home' : 'away'}-${String(player.shirt)}`}
						at={toScreen(player.at)}
						shirt={player.shirt}
						home={player.home}
						yours={yours === (player.home ? 'home' : 'away')}
					/>
				))}
			</g>
			<circle className="pitch__ball" data-testid="moving-pitch-ball" cx={ball[0]} cy={ball[1]} r={0.95} />
		</svg>
	)
}

export default MovingPitch
