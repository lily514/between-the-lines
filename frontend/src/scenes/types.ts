// The scene fixtures (`btl scene-fixtures` writes them) and the specs that draw a concept's scene from one.
import type { Band } from '../api/client.ts'

/** A point in picture metres: the team on the ball attacks towards x = 105. */
export type Point = readonly [number, number]
export type Side = 'attacking' | 'defending'

export interface Fact {
	value: unknown
	display: string
}

export interface SceneMarker {
	home: boolean
	role: string
	shirt: number
	side: Side
	x: number
	y: number
}

/** One touch of the play, with seconds from the first; the last is where the ball arrives ("end"). */
export interface SceneTouch {
	action_id: number
	at: number
	x: number
	y: number
	action: string
	result?: string
	side?: Side
	shirt?: number
}

export interface SceneQuestion {
	asks: string
	form: string
	text: string
	options: string[]
	correct: string
}

/** One real moment per active concept: the evidence pack, the key frame, the timed play and the questions. */
export interface SceneFixture {
	concept: string
	name: string
	strand: string
	detector: string | null
	evidence_fields: string[]
	match: { seed: number; home: string; away: string; home_code: string; away_code: string }
	moment: {
		action_id: number
		span: number[]
		clock: string
		difficulty: number
		phase: string
		evidence: Record<string, number>
	}
	pack: {
		asks: string
		form: string
		level: number
		context: Record<string, Fact>
		outcome: Record<string, Fact>
		picture: {
			action_id: number
			ball: number[]
			mark: number[] | null
			markers: SceneMarker[]
			path: number[][]
		}
		reveal_path: number[][]
		reveal_line: number | null
		correct_key: string
	}
	snapshot: { action_id: number; ball: number[]; markers: SceneMarker[] }
	path: SceneTouch[]
	questions: Record<string, SceneQuestion>
}

export interface MarkerRef {
	side: Side
	shirt: number
}

/** When in the story (0 to 1) something appears, and optionally when it goes. */
export type Beat = number

interface Timed {
	beat?: Beat
	until?: Beat
}

/**
 * What a layer draws, in picture metres. Every text is a template over the pack's facts, such as `GAP {gap_m} m`;
 * the scene fills it and never computes a number.
 */
export type SceneItem =
	/** One big word on the pitch: "OFFSIDE", "FOUL". */
	| ({ kind: 'word'; text: string; at: Point } & Timed)
	/** A short mono label. */
	| ({ kind: 'label'; text: string; at: Point; anchor?: 'start' | 'middle' | 'end' } & Timed)
	/** A label at the edge of the view; `x` (picture) sets the height of a right-edge label. */
	| ({ kind: 'edge-label'; text: string; edge: 'right' | 'bottom'; x?: number } & Timed)
	/** Defenders as a shaded band across the pitch at picture x; `lit` draws it stronger, when a pass gets past. */
	| ({ kind: 'wall'; x: number; depth?: number; lit?: boolean } & Timed)
	/** A line across the pitch at picture x, named at the right edge. */
	| ({ kind: 'line'; x: number; label?: string } & Timed)
	/** A rectangle, outlined or shaded, with an optional label inside. */
	| ({ kind: 'zone'; from: Point; to: Point; fill?: boolean; label?: string } & Timed)
	/** A ring round a spot: where the ball went out, or was placed. */
	| ({ kind: 'ring'; at: Point; r?: number } & Timed)
	/** A ring that closes in and fades, from `beat` to `until`. */
	| { kind: 'halo'; at: Point; r?: number; beat: Beat; until: Beat }
	/** A cross where contact was made. */
	| ({ kind: 'cross'; at: Point } & Timed)
	/** A measuring bracket with a label beside it. */
	| ({ kind: 'bracket'; from: Point; to: Point; label: string } & Timed)
	/** A small numbered badge, such as the lines a pass broke. */
	| ({ kind: 'badge'; at: Point; text: string } & Timed)
	/** A pill at the top left of the view, such as a timer; several with beats make it count. */
	| ({ kind: 'pill'; text: string } & Timed)
	/** The assistant referee's flag at the right edge, down or up. */
	| ({ kind: 'flag'; up: boolean } & Timed)
	/** A yellow card beside a player. */
	| ({ kind: 'card'; at: Point } & Timed)
	/** A faded copy of a player where they stood, such as "level when played". */
	| ({ kind: 'ghost'; marker: MarkerRef; label?: string } & Timed)
	/** The threat grid over the whole pitch: cells along by across. */
	| { kind: 'grid'; cells: readonly [number, number] }
	/** A player moving `by` picture metres between two beats; `arrive` starts them displaced and ends them where they stood. */
	| { kind: 'move'; marker: MarkerRef; by: Point; from: Beat; to: Beat; arrive?: boolean }
	/** More players drawn at full strength. */
	| { kind: 'involve'; markers: MarkerRef[] }

/** What a spec gets to draw from: the fixture, its facts as shown, and the play's touches with their beats. */
export interface SceneData {
	fixture: SceneFixture
	/** Each fact's display text, context and outcome together. */
	facts: Record<string, string>
	touches: SceneTouch[]
	/** The story beat of each touch, the first at BALL_STARTS and the last at BALL_ARRIVES. */
	beats: number[]
	markers: SceneMarker[]
	/** The offside line's picture x, when the pack has one. */
	line: number | null
}

/** The ball's place at a beat; two at the same beat move it without travelling (a restart). */
export interface TrackPoint {
	beat: Beat
	at: Point
}

export interface SceneSpec {
	concept: string
	/** The frame shown when motion is reduced: the start, or the end so the call is visible. */
	still: 'start' | 'end'
	/** Picture points the view must show, beyond the play and the players in it. */
	focus?: (scene: SceneData) => Point[]
	/** The ball's track when it isn't the play's path. */
	track?: (scene: SceneData) => TrackPoint[]
	layers: Record<Band, (scene: SceneData) => SceneItem[]>
}
