// Fouls and cards: the contact, the call, the ball placed where it happened, and what the referee gave.
import { at, beatOf, ref, toucher } from './helpers.ts'
import type { Point, SceneData, SceneItem, SceneSpec } from './types.ts'

const CALL_AT = 0.14
const PLACED_AT = 0.3
const GIVEN_AT = 0.5

const spot = (scene: SceneData): Point => {
	const foul = scene.touches[0]
	return foul === undefined ? [0, 0] : at(foul)
}

/** The player who fouled steps back from the ball. */
const standsBack = (scene: SceneData): SceneItem[] => {
	const fouler = toucher(scene, scene.touches[0])
	if (fouler === undefined) return []
	return [{ kind: 'move', marker: ref(fouler), by: [-2.5, 0], from: PLACED_AT, to: GIVEN_AT }]
}

/** A card beside the player, when the booking note says there was one. */
const card = (scene: SceneData): SceneItem[] => {
	const fouler = toucher(scene, scene.touches[0])
	if (fouler === undefined || (scene.facts.booking_note ?? '') === '') return []
	return [{ kind: 'card', at: [fouler.x, fouler.y], beat: GIVEN_AT - 0.1 }]
}

const spec: SceneSpec = {
	concept: 'fouls_and_cards',
	still: 'end',
	layers: {
		getting_there: scene => [
			{ kind: 'cross', at: spot(scene), beat: 0.05 },
			{ kind: 'word', text: 'FOUL', at: [spot(scene)[0] + 4, spot(scene)[1]], beat: CALL_AT },
			{ kind: 'ring', at: spot(scene), r: 2.4, beat: PLACED_AT },
			...standsBack(scene),
			{ kind: 'word', text: '{RESTART_TYPE}', at: [spot(scene)[0] - 5, spot(scene)[1]], beat: GIVEN_AT }
		],
		solid: scene => [
			{ kind: 'cross', at: spot(scene), beat: 0.05 },
			{ kind: 'word', text: 'FOUL', at: [spot(scene)[0] + 4, spot(scene)[1]], beat: CALL_AT },
			{ kind: 'label', text: '{BOX_POSITION}', at: [spot(scene)[0] + 7, spot(scene)[1]], beat: 0.22 },
			{ kind: 'ring', at: spot(scene), r: 2.4, beat: PLACED_AT },
			...standsBack(scene),
			...card(scene),
			{ kind: 'edge-label', text: '{FOUL_OUTCOME}', edge: 'bottom', beat: GIVEN_AT }
		],
		sharp: scene => [
			{ kind: 'cross', at: spot(scene), beat: 0.05 },
			{
				kind: 'label',
				text: 'CONTACT',
				at: [spot(scene)[0] + 3, spot(scene)[1] + 3.5],
				anchor: 'start',
				beat: 0.08
			},
			{ kind: 'label', text: '{BOX_POSITION}', at: [spot(scene)[0] + 7, spot(scene)[1]], beat: 0.22 },
			{ kind: 'ring', at: spot(scene), r: 2.4, beat: PLACED_AT },
			...standsBack(scene),
			...card(scene),
			{
				kind: 'edge-label',
				text: '{RESTART_TYPE}',
				edge: 'right',
				x: spot(scene)[0] - 8,
				beat: beatOf(scene, 'freekick_short') - 0.02
			},
			{ kind: 'edge-label', text: '{FOUL_OUTCOME}', edge: 'bottom', beat: GIVEN_AT }
		]
	}
}

export default spec
