import type { Point } from './index.support.ts'

export interface PlayerMarkProps {
	/** Where to draw the player, in screen metres. */
	at: Point
	shirt: number
	home: boolean
	/** Whether the player is on the viewer's team: they get a dashed ring. */
	yours: boolean
	/** Whether the player steps back because they're away from the moment. */
	dim?: boolean
}

/** A player as every pitch draws them: home a filled disc with the shirt number, away a ring, so colour is never
 * the only signal. */
const PlayerMark = ({ at: [x, y], shirt, home, yours, dim = false }: PlayerMarkProps) => {
	const shape = home ? 'home' : 'away'
	return (
		<g
			className={`pitch__player pitch__player--${shape}${dim ? ' pitch__player--dim' : ''}`}
			data-testid={`player-${shape}`}>
			{yours && <circle className="pitch__yours" data-testid="pitch-yours" cx={x} cy={y} r={3.1} />}
			{home ? (
				<>
					<circle cx={x} cy={y} r={2.2} />
					<text x={x} y={y + 0.85}>
						{shirt}
					</text>
				</>
			) : (
				<circle cx={x} cy={y} r={1.8} />
			)}
		</g>
	)
}

export default PlayerMark
