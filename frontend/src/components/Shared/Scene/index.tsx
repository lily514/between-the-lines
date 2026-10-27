import { useId, useState } from 'react'
import type { Band } from '../../../api/client.ts'
import type { Point, SceneData, SceneFixture, SceneItem, SceneMarker, SceneSpec } from '../../../scenes/types.ts'
import {
	FULL_VIEW,
	MARKINGS,
	PITCH_LENGTH,
	PITCH_WIDTH,
	pathData,
	toScreen,
	viewBoxText
} from '../Pitch/index.support.ts'
import '../Pitch/index.css'
import './index.css'
import useReducedMotion from '../useReducedMotion.ts'
import {
	appearFrames,
	ballTrack,
	cellOf,
	cssName,
	focusPoints,
	haloFrames,
	isInvolved,
	layerItems,
	loop,
	round,
	same,
	sceneData,
	sceneView,
	shownInStill,
	trackStops,
	travelFrames
} from './index.support.ts'

export interface SceneProps {
	spec: SceneSpec
	fixture: SceneFixture
	band: Band
	/** Names the scene for the pause button: "Pause motion in the Offside scene". */
	name: string
}

const PLAYER_R = 2.2
const RING_R = 1.8
const BALL_R = 0.95
/** On-pitch text is at least 1.9 units (about 13 px at 350 px wide). */
const LABEL_SIZE = 1.9
const CHAR_WIDTH = LABEL_SIZE * 0.62

/**
 * A concept's scene (B1 to B4): the key frame of a real moment, the play's path, and the layer for the viewer's level
 * drawn over it. Motion is a 5 s CSS loop the viewer can pause; with reduced motion a still frame shows instead. The
 * SVG is decorative: the step's title, paragraph and example carry the meaning.
 */
const Scene = ({ spec, fixture, band, name }: SceneProps) => {
	const id = useId()
	const [paused, setPaused] = useState(false)
	const reduced = useReducedMotion()
	const scene = sceneData(fixture)
	const items = layerItems(spec, band, scene)
	const track = ballTrack(spec, scene)
	const view = sceneView(focusPoints(spec, scene, items))
	const still = reduced ? spec.still : null
	const trackPoints = track.map(point => point.at)
	const shown = still === null ? items : items.filter(item => shownInStill(item, still))
	const frames: string[] = []
	const key = (suffix: string) => cssName(id, suffix)

	const stops = trackStops(track)
	const ballStart = toScreen(track[0]?.at ?? [0, 0])
	const ballEnd = stops.at(-1) ?? { dx: 0, dy: 0 }
	frames.push(travelFrames(key('ball'), stops))
	const pathPoints = trackPoints.map(toScreen)

	const moves = items.flatMap(item => (item.kind === 'move' ? [item] : []))
	const moveOf = (marker: SceneMarker) => moves.find(move => same(move.marker, marker))

	const edge = {
		right: view.x + view.width - 1.2,
		bottom: view.y + view.height - 1.6,
		left: view.x + 1.5,
		top: view.y + 1.5
	}

	const beatStyle = (index: number, beat = 0, until?: number) => {
		if (still !== null) return {}
		const frame = appearFrames(key(`i${String(index)}`), beat, until)
		if (frame === '') return {}
		frames.push(frame)
		return { animation: loop(key(`i${String(index)}`)), opacity: 0 }
	}

	const drawn = shown.map((item, index) => drawItem(item, index, scene, view, edge, beatStyle, still, key, frames))
	const under = drawn.filter(part => part?.layer === 'under').map(part => part?.node)
	const over = drawn.filter(part => part?.layer === 'over').map(part => part?.node)

	return (
		<div className="scene">
			<svg
				className={`scene__svg${paused ? ' scene__svg--paused' : ''}${still === null ? ' scene__svg--moving' : ''}`}
				viewBox={viewBoxText(view)}
				aria-hidden="true"
				focusable="false"
				data-band={band}
				data-still={still ?? undefined}>
				{still === null && <style>{frames.join('\n')}</style>}
				<rect
					className="pitch__grass"
					x={FULL_VIEW.x}
					y={FULL_VIEW.y}
					width={FULL_VIEW.width}
					height={FULL_VIEW.height}
				/>
				<g className="pitch__markings">
					<rect {...MARKINGS.outline} />
					<line x1={0} y1={MARKINGS.halfway} x2={PITCH_WIDTH} y2={MARKINGS.halfway} />
					<circle cx={MARKINGS.centre.x} cy={MARKINGS.centre.y} r={MARKINGS.centre.r} />
					{MARKINGS.boxes.map(box => (
						<rect key={`${String(box.y)}-${String(box.width)}`} {...box} />
					))}
					{MARKINGS.spots.map(([x, y]) => (
						<circle key={y} className="pitch__spot" cx={x} cy={y} r={0.3} />
					))}
				</g>
				<g className={still === null ? 'scene__story' : undefined}>
					{under}
					{pathPoints.length > 1 && (
						<path
							className="scene__path"
							d={pathData(pathPoints)}
							pathLength={1}
							style={
								still === null
									? { animation: loop(key('path')), strokeDashoffset: 1 }
									: { strokeDashoffset: still === 'end' ? 0 : 1 }
							}
						/>
					)}
					<g className="pitch__players">
						{players(scene, trackPoints, items).map(marker => {
							const [x, y] = toScreen([marker.x, marker.y])
							const move = moveOf(marker)
							const moved =
								move === undefined ? null : moveStyle(move, index(moves, move), key, frames, still)
							const dim = !isInvolved(marker, trackPoints, items)
							const shape = marker.home ? 'home' : 'away'
							return (
								<g
									key={`${marker.side}-${String(marker.shirt)}`}
									className={`pitch__player pitch__player--${shape}${dim ? ' pitch__player--dim' : ''}`}
									data-testid={`scene-player-${marker.side}`}
									style={moved ?? undefined}>
									{marker.home ? (
										<>
											<circle cx={x} cy={y} r={PLAYER_R} />
											<text x={x} y={y + 0.85}>
												{marker.shirt}
											</text>
										</>
									) : (
										<circle cx={x} cy={y} r={RING_R} />
									)}
								</g>
							)
						})}
					</g>
					<circle
						className="pitch__ball scene__ball"
						data-testid="scene-ball"
						cx={ballStart[0]}
						cy={ballStart[1]}
						r={BALL_R}
						style={
							still === null
								? { animation: loop(key('ball'), 'ease-in-out') }
								: still === 'end'
									? {
											transform: `translate(${String(round(ballEnd.dx))}px, ${String(round(ballEnd.dy))}px)`
										}
									: undefined
						}
					/>
					{over}
				</g>
			</svg>
			{still === null && (
				<button
					type="button"
					className="scene__pause"
					aria-pressed={paused}
					aria-label={`${paused ? 'Play' : 'Pause'} motion in the ${name} scene`}
					onClick={() => {
						setPaused(!paused)
					}}>
					{paused ? 'Play motion' : 'Pause motion'}
				</button>
			)}
		</div>
	)
}

/** Players under movers, home over away within each, so numbers stay readable. */
const players = (scene: SceneData, track: readonly Point[], items: readonly SceneItem[]) =>
	[...scene.markers].sort(
		(a, b) =>
			Number(isInvolved(a, track, items)) * 2 +
			Number(a.home) -
			(Number(isInvolved(b, track, items)) * 2 + Number(b.home))
	)

const index = <T,>(list: readonly T[], item: T) => list.indexOf(item)

type Still = 'start' | 'end' | null
type BeatStyle = (index: number, beat?: number, until?: number) => { animation?: string; opacity?: number }
interface Edge {
	right: number
	bottom: number
	left: number
	top: number
}

const moveStyle = (
	move: Extract<SceneItem, { kind: 'move' }>,
	n: number,
	key: (suffix: string) => string,
	frames: string[],
	still: Still
) => {
	const [dx, dy] = [-move.by[1], -move.by[0]]
	const from = move.arrive ? { dx: -dx, dy: -dy } : { dx: 0, dy: 0 }
	const to = move.arrive ? { dx: 0, dy: 0 } : { dx, dy }
	if (still !== null) {
		const rest = still === 'end' ? to : from
		return { transform: `translate(${String(round(rest.dx))}px, ${String(round(rest.dy))}px)` }
	}
	const name = key(`m${String(n)}`)
	frames.push(
		travelFrames(name, [
			{ beat: 0, ...from },
			{ beat: move.from, ...from },
			{ beat: move.to, ...to }
		])
	)
	return { animation: loop(name, 'ease-in-out') }
}

interface Drawn {
	layer: 'under' | 'over'
	node: React.ReactNode
}

const drawItem = (
	item: SceneItem,
	n: number,
	scene: SceneData,
	view: { x: number; y: number; width: number; height: number },
	edge: Edge,
	beatStyle: BeatStyle,
	still: Still,
	key: (suffix: string) => string,
	frames: string[]
): Drawn | null => {
	const k = `item-${String(n)}`
	switch (item.kind) {
		case 'word': {
			const [x, y] = toScreen(item.at)
			return over(
				<text key={k} className="scene__word" x={x} y={y} style={beatStyle(n, item.beat, item.until)}>
					{item.text}
				</text>
			)
		}
		case 'label': {
			const [x, y] = toScreen(item.at)
			return over(
				<text
					key={k}
					className="scene__label"
					x={x}
					y={y}
					textAnchor={item.anchor ?? 'middle'}
					style={beatStyle(n, item.beat, item.until)}>
					{item.text}
				</text>
			)
		}
		case 'edge-label': {
			const y = item.edge === 'right' && item.x !== undefined ? PITCH_LENGTH - item.x - 0.8 : edge.bottom
			return over(
				<text
					key={k}
					className="scene__label"
					x={edge.right}
					y={y}
					textAnchor="end"
					style={beatStyle(n, item.beat, item.until)}>
					{item.text}
				</text>
			)
		}
		case 'wall': {
			const depth = item.depth ?? 3.6
			return under(
				<rect
					key={k}
					className={`scene__wall${item.lit ? ' scene__wall--lit' : ''}`}
					x={view.x}
					y={PITCH_LENGTH - item.x - depth / 2}
					width={view.width}
					height={depth}
					style={beatStyle(n, item.beat, item.until)}
				/>
			)
		}
		case 'line': {
			const y = PITCH_LENGTH - item.x
			return under(
				<g key={k} style={beatStyle(n, item.beat, item.until)}>
					<line className="scene__line" x1={view.x} y1={y} x2={view.x + view.width} y2={y} />
					{item.label !== undefined && (
						<text className="scene__label" x={edge.right} y={y - 0.8} textAnchor="end">
							{item.label}
						</text>
					)}
				</g>
			)
		}
		case 'zone': {
			const [x1, y1] = toScreen(item.from)
			const [x2, y2] = toScreen(item.to)
			const [x, y] = [Math.min(x1, x2), Math.min(y1, y2)]
			const [w, h] = [Math.abs(x2 - x1), Math.abs(y2 - y1)]
			return under(
				<g key={k} style={beatStyle(n, item.beat, item.until)}>
					<rect
						className={`scene__zone${item.fill ? ' scene__zone--fill' : ''}`}
						x={x}
						y={y}
						width={w}
						height={h}
					/>
					{item.label !== undefined && (
						<text className="scene__label" x={x + w / 2} y={y + h / 2 + 0.7} textAnchor="middle">
							{item.label}
						</text>
					)}
				</g>
			)
		}
		case 'ring': {
			const [x, y] = toScreen(item.at)
			return over(
				<circle
					key={k}
					className="scene__ring"
					cx={x}
					cy={y}
					r={item.r ?? 2.6}
					style={beatStyle(n, item.beat, item.until)}
				/>
			)
		}
		case 'halo': {
			const [x, y] = toScreen(item.at)
			const name = key(`h${String(n)}`)
			let style: React.CSSProperties = {}
			if (still === null) {
				frames.push(haloFrames(name, item.beat, item.until))
				style = { animation: loop(name, 'ease-out'), opacity: 0 }
			} else if (still === 'start') {
				style = { opacity: 0 }
			}
			return over(<circle key={k} className="scene__halo" cx={x} cy={y} r={item.r ?? 5.6} style={style} />)
		}
		case 'cross': {
			const [x, y] = toScreen(item.at)
			return over(
				<g key={k} className="scene__cross" style={beatStyle(n, item.beat, item.until)}>
					<line x1={x - 1.1} y1={y - 1.1} x2={x + 1.1} y2={y + 1.1} />
					<line x1={x + 1.1} y1={y - 1.1} x2={x - 1.1} y2={y + 1.1} />
				</g>
			)
		}
		case 'bracket': {
			const [x1, y1] = toScreen(item.from)
			const [x2, y2] = toScreen(item.to)
			const length = Math.hypot(x2 - x1, y2 - y1) || 1
			const [nx, ny] = [(-(y2 - y1) / length) * 0.7, ((x2 - x1) / length) * 0.7]
			const [mx, my] = [(x1 + x2) / 2, (y1 + y2) / 2]
			const across = Math.abs(x2 - x1) > Math.abs(y2 - y1)
			return over(
				<g key={k} className="scene__bracket" style={beatStyle(n, item.beat, item.until)}>
					<line x1={x1} y1={y1} x2={x2} y2={y2} />
					<line x1={x1 + nx} y1={y1 + ny} x2={x1 - nx} y2={y1 - ny} />
					<line x1={x2 + nx} y1={y2 + ny} x2={x2 - nx} y2={y2 - ny} />
					<text
						className="scene__label"
						x={across ? mx : mx + 1.4}
						y={across ? my - 1.2 : my + 0.7}
						textAnchor={across ? 'middle' : 'start'}>
						{item.label}
					</text>
				</g>
			)
		}
		case 'badge': {
			const [x, y] = toScreen(item.at)
			return over(
				<g key={k} className="scene__badge" style={beatStyle(n, item.beat, item.until)}>
					<circle cx={x} cy={y} r={1.8} />
					<text x={x} y={y + 0.8}>
						{item.text}
					</text>
				</g>
			)
		}
		case 'pill': {
			const width = item.text.length * CHAR_WIDTH + 3
			return over(
				<g key={k} className="scene__pill" style={beatStyle(n, item.beat, item.until)}>
					<rect x={edge.left} y={edge.top} width={width} height={4.6} rx={2.3} />
					<text x={edge.left + 1.5} y={edge.top + 3.2} textAnchor="start">
						{item.text}
					</text>
				</g>
			)
		}
		case 'flag': {
			const x = edge.right - 1.2
			const y = view.y + view.height / 2
			return over(
				<g key={k} className="scene__flag" style={beatStyle(n, item.beat, item.until)}>
					<line x1={x} y1={y - 2} x2={x} y2={y + 2} />
					{item.up ? (
						<rect x={x} y={y - 2} width={2.4} height={1.9} />
					) : (
						<rect x={x} y={y + 0.4} width={2} height={1.6} />
					)}
				</g>
			)
		}
		case 'card': {
			const [x, y] = toScreen(item.at)
			return over(
				<rect
					key={k}
					className="scene__card"
					x={x + 2.4}
					y={y - 3.6}
					width={1.6}
					height={2.2}
					rx={0.2}
					style={beatStyle(n, item.beat, item.until)}
				/>
			)
		}
		case 'ghost': {
			const marker = scene.markers.find(m => same(item.marker, m))
			if (marker === undefined) return null
			const [x, y] = toScreen([marker.x, marker.y])
			return under(
				<g key={k} className="scene__ghost" style={beatStyle(n, item.beat, item.until)}>
					<circle cx={x} cy={y} r={marker.home ? PLAYER_R : RING_R} />
					{item.label !== undefined && (
						<text className="scene__label" x={x} y={y + PLAYER_R + 2.2} textAnchor="middle">
							{item.label}
						</text>
					)}
				</g>
			)
		}
		case 'grid': {
			const [along, across] = item.cells
			const cells = Array.from({ length: along * across }, (_, i) => {
				const column = i % along
				const row = Math.floor(i / along)
				const { from, to } = cellOf(
					[column * (PITCH_LENGTH / along) + 0.1, row * (PITCH_WIDTH / across) + 0.1],
					item.cells
				)
				const [x1, y1] = toScreen(from)
				const [x2, y2] = toScreen(to)
				return (
					<rect
						key={i}
						x={Math.min(x1, x2)}
						y={Math.min(y1, y2)}
						width={Math.abs(x2 - x1)}
						height={Math.abs(y2 - y1)}
					/>
				)
			})
			return under(
				<g key={k} className="scene__grid">
					{cells}
				</g>
			)
		}
		case 'move':
		case 'involve':
			return null
	}
}

const over = (node: React.ReactNode): Drawn => ({ layer: 'over', node })
const under = (node: React.ReactNode): Drawn => ({ layer: 'under', node })

export default Scene
