// Restarts: the ball goes out, where it crossed is marked, and someone goes to take the restart.
import { at, beatOf, endOf, nearest, toucher, upper } from './helpers.ts'
import type { Point, SceneData, SceneSpec, TrackPoint } from './types.ts'

/** Where the ball crossed the line: the end of the picture's path, or the restart's spot. */
const outPoint = (scene: SceneData): Point => {
	const last = scene.fixture.pack.picture.path.at(-1)
	return last === undefined ? restartSpot(scene) : [last[0] ?? 0, last[1] ?? 0]
}

const restartSpot = (scene: SceneData): Point => {
	const touch = scene.touches[1] ?? scene.touches[0]
	return touch === undefined ? [0, 0] : at(touch)
}

const OUT_AT = 0.3
const RESTART_AT = 0.5

const track = (scene: SceneData): TrackPoint[] => {
	const first = scene.touches[0]
	const start: Point = first === undefined ? [0, 0] : at(first)
	return [
		{ beat: scene.beats[0] ?? 0, at: start },
		{ beat: OUT_AT, at: outPoint(scene) },
		{ beat: RESTART_AT, at: outPoint(scene) },
		{ beat: RESTART_AT, at: restartSpot(scene) },
		{ beat: scene.beats.at(-1) ?? 0.75, at: endOf(scene) }
	]
}

/** The nearest player of the restarting side walks to the spot to take it. */
const taker = (scene: SceneData) => {
	const spot = restartSpot(scene)
	const second = scene.touches[1]
	const takerSide = second?.side ?? 'defending'
	const player = toucher(scene, second) ?? nearest(scene, takerSide, spot, 1)[0]
	if (player === undefined || Math.hypot(player.x - spot[0], player.y - spot[1]) > 25) return []
	return [
		{
			kind: 'move' as const,
			marker: { side: player.side, shirt: player.shirt },
			by: [spot[0] - player.x, spot[1] - player.y] as const,
			from: OUT_AT,
			to: RESTART_AT
		}
	]
}

const spec: SceneSpec = {
	concept: 'restarts',
	still: 'start',
	focus: scene => [outPoint(scene), restartSpot(scene)],
	track,
	layers: {
		getting_there: scene => [{ kind: 'ring', at: outPoint(scene), beat: OUT_AT }, ...taker(scene)],
		solid: scene => {
			const passer = scene.touches[0]
			return [
				...(passer === undefined
					? []
					: [
							{
								kind: 'label' as const,
								text: 'LAST TOUCH',
								at: at(passer),
								beat: beatOf(scene, 'pass') + 0.02
							}
						]),
				{ kind: 'ring', at: outPoint(scene), beat: OUT_AT },
				...taker(scene),
				{
					kind: 'label',
					text: '{RESTART_TYPE} · {RESTART_TEAM}',
					at: restartSpot(scene),
					anchor: 'start',
					beat: RESTART_AT
				}
			]
		},
		sharp: scene => {
			const passer = scene.touches[0]
			return [
				...(passer === undefined
					? []
					: [
							{
								kind: 'label' as const,
								text: `LAST IN DATA: ${upper(passer.action)}`,
								at: at(passer),
								beat: beatOf(scene, 'pass') + 0.02
							}
						]),
				{ kind: 'ring', at: outPoint(scene), beat: OUT_AT },
				{ kind: 'label', text: 'OUT', at: outPoint(scene), anchor: 'start', beat: OUT_AT + 0.05 },
				...taker(scene),
				{ kind: 'label', text: '→ {restart_type}', at: restartSpot(scene), anchor: 'start', beat: RESTART_AT },
				{ kind: 'edge-label', text: 'RESTART FROM THE LAST TOUCH IN THE DATA', edge: 'bottom', beat: 0.6 }
			]
		}
	}
}

export default spec
