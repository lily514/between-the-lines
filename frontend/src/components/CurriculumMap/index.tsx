import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import type { ConceptMap, MapConcept } from '../../api/client.ts'
import { percent } from '../Shared/ProgressBar.support.ts'
import { BAND, buildsOn, FOOT, MAP_WIDTH, place, startingConcept, type PlacedConcept } from './index.support.ts'
import './index.css'

export interface CurriculumMapProps {
	/** The map; null while it loads. */
	map: ConceptMap | null
	error: string | null
	/** Close the map and go back to the screen underneath, as it was. */
	onBack: () => void
}

const NODE_R = 3
const RING = 2 * Math.PI * NODE_R

/** "Your pitch" (CM-A): every concept there is to learn, by strand across and tier up the pitch, deepest at the top.
 *
 * Concepts asked about now show the viewer's level; the rest are coming later, drawn dashed. Choosing one (tap, or
 * focus and Enter) fills the card below and draws what it builds on; choosing one from the list opens its card in a
 * dialog, so the viewer need not scroll back up. It opens over whatever screen the viewer was on; Back or Esc closes
 * it. */
const CurriculumMap = ({ map, error, onBack }: CurriculumMapProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const [chosen, setChosen] = useState<string | null>(null)
	const [listed, setListed] = useState<string | null>(null)

	useEffect(() => {
		heading.current?.focus()
	}, [])

	useEffect(() => {
		const close = (event: globalThis.KeyboardEvent) => {
			if (event.key === 'Escape') onBack()
		}
		document.addEventListener('keydown', close)
		return () => {
			document.removeEventListener('keydown', close)
		}
	}, [onBack])

	const selected = map === null ? null : (map.concepts.find(c => c.key === chosen) ?? startingConcept(map))
	const shown = map?.concepts.find(c => c.key === listed)
	return (
		<section className="curriculum-map" aria-labelledby={headingId}>
			<button
				type="button"
				className="text-button curriculum-map__back"
				aria-label="Close the map and go back to where you were"
				onClick={onBack}>
				← Back
			</button>
			<div className="curriculum-map__title">
				<h2 id={headingId} ref={heading} tabIndex={-1} className="curriculum-map__heading screen-heading">
					Your pitch
				</h2>
				{map !== null && (
					<span className="curriculum-map__count">
						{
							map.concepts.filter(
								c => c.askable && c.mastery !== null && c.mastery >= map.thresholds.mastery
							).length
						}{' '}
						of {map.concepts.length} mastered
					</span>
				)}
			</div>
			<p className="curriculum-map__intro">
				Everything Between the Lines can teach, laid out like a pitch. You attack upwards: the higher up, the
				deeper the idea.
			</p>
			{error !== null && (
				<p className="curriculum-map__error" role="alert">
					{error}
				</p>
			)}
			{map === null && error === null && <p role="status">Finding the map…</p>}
			{map !== null && selected !== null && (
				<>
					<Pitch map={map} selected={selected} onChoose={setChosen} />
					<Legend />
					<ConceptCard map={map} concept={selected} />
					<details className="curriculum-map__list">
						<summary>All {map.concepts.length} concepts as a list</summary>
						{map.strands.map(strand => (
							<section key={strand.key} aria-label={strand.name}>
								<h3 className="curriculum-map__strand-name">{strand.name}</h3>
								<ul>
									{map.concepts
										.filter(concept => concept.strand === strand.key)
										.map(concept => (
											<li key={concept.key}>
												<button
													type="button"
													className="text-button"
													aria-pressed={concept.key === selected.key}
													onClick={() => {
														setChosen(concept.key)
														setListed(concept.key)
													}}>
													{concept.name}
												</button>{' '}
												<span className="curriculum-map__level">{levelText(concept)}</span>
											</li>
										))}
								</ul>
							</section>
						))}
					</details>
					{shown !== undefined && (
						<ConceptDialog
							map={map}
							concept={shown}
							onClose={() => {
								setListed(null)
							}}
						/>
					)}
				</>
			)}
		</section>
	)
}

/** A concept's level in words, or that it is coming later. */
const levelText = (concept: MapConcept) => (concept.askable ? (concept.level ?? 'Asked now') : 'Coming later')

interface PitchProps {
	map: ConceptMap
	selected: MapConcept
	onChoose: (key: string) => void
}

const Pitch = ({ map, selected, onChoose }: PitchProps) => {
	const placed = place(map)
	const at = (key: string) => placed.find(p => p.concept.key === key)
	const chain = [selected, ...buildsOn(map, selected.key)]
	const arrows = chain.flatMap(concept =>
		concept.prerequisites.flatMap(before => {
			const from = at(before)
			const to = at(concept.key)
			return from === undefined || to === undefined ? [] : [{ from, to }]
		})
	)
	const height = map.tiers.length * BAND + FOOT
	const columns = map.strands.length
	return (
		<div className="curriculum-map__pitch">
			<div className="curriculum-map__strands" aria-hidden="true">
				{map.strands.map(strand => (
					<span key={strand.key}>{strand.name}</span>
				))}
			</div>
			<svg
				viewBox={`0 0 ${String(MAP_WIDTH)} ${String(height)}`}
				className="curriculum-map__svg"
				role="group"
				aria-label="Curriculum map">
				<defs>
					<marker
						id="curriculum-arrow"
						viewBox="0 0 6 6"
						refX="5"
						refY="3"
						markerWidth="3"
						markerHeight="3"
						orient="auto">
						<path d="M0 0L6 3L0 6z" className="curriculum-map__arrow-head" />
					</marker>
				</defs>
				<rect width={MAP_WIDTH} height={height} className="curriculum-map__grass" />
				{map.tiers.map((tier, index) => (
					<g key={tier}>
						{index % 2 === 1 && (
							<rect
								y={(map.tiers.length - 1 - index) * BAND}
								width={MAP_WIDTH}
								height={BAND}
								className="curriculum-map__band"
							/>
						)}
						<text x={1.2} y={(map.tiers.length - 1 - index) * BAND + 2.8} className="curriculum-map__tier">
							T{index} · {tier.toUpperCase()}
						</text>
					</g>
				))}
				<line
					x1={0}
					y1={(map.tiers.length * BAND) / 2}
					x2={MAP_WIDTH}
					y2={(map.tiers.length * BAND) / 2}
					className="curriculum-map__line"
				/>
				<circle cx={MAP_WIDTH / 2} cy={(map.tiers.length * BAND) / 2} r={7} className="curriculum-map__line" />
				{Array.from({ length: columns - 1 }, (_, i) => (
					<line
						key={i}
						x1={(MAP_WIDTH / columns) * (i + 1)}
						x2={(MAP_WIDTH / columns) * (i + 1)}
						y1={0}
						y2={height}
						className="curriculum-map__divider"
					/>
				))}
				{arrows.map(({ from, to }) => (
					<line
						key={`${from.concept.key}-${to.concept.key}`}
						x1={from.x}
						y1={from.y - NODE_R - 0.6}
						x2={to.x}
						y2={to.y + NODE_R + 0.6}
						className="curriculum-map__arrow"
						markerEnd="url(#curriculum-arrow)"
					/>
				))}
				{placed.map(node => (
					<Node
						key={node.concept.key}
						node={node}
						selected={node.concept.key === selected.key}
						onChoose={onChoose}
					/>
				))}
			</svg>
		</div>
	)
}

interface NodeProps {
	node: PlacedConcept
	selected: boolean
	onChoose: (key: string) => void
}

const Node = ({ node, selected, onChoose }: NodeProps) => {
	const { concept, x, y, lines, state } = node
	const choose = () => {
		onChoose(concept.key)
	}
	const onKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault()
			choose()
		}
	}
	const share = concept.mastery ?? 0
	return (
		<g
			role="button"
			tabIndex={0}
			aria-label={`${concept.name}: ${levelText(concept)}`}
			aria-pressed={selected}
			className={`curriculum-map__node curriculum-map__node--${state}`}
			onClick={choose}
			onFocus={choose}
			onKeyDown={onKeyDown}>
			{selected && <circle cx={x} cy={y} r={NODE_R + 1.4} className="curriculum-map__halo" />}
			<circle cx={x} cy={y} r={NODE_R} className="curriculum-map__dot" />
			{state === 'asked' && (
				<circle
					cx={x}
					cy={y}
					r={NODE_R}
					className="curriculum-map__arc"
					strokeDasharray={`${String(share * RING)} ${String(RING)}`}
					transform={`rotate(-90 ${String(x)} ${String(y)})`}
				/>
			)}
			{state === 'mastered' && (
				<path d={`M${String(x - 1.3)} ${String(y)}l1 1.1l1.8-2.2`} className="curriculum-map__tick" />
			)}
			{state === 'later' && <circle cx={x} cy={y} r={0.6} className="curriculum-map__pip" />}
			<text x={x} y={y + NODE_R + 2.6} className="curriculum-map__label">
				{lines.map((line, i) => (
					<tspan key={line} x={x} dy={i === 0 ? 0 : 2.6}>
						{line}
					</tspan>
				))}
			</text>
		</g>
	)
}

const Legend = () => (
	<ul className="curriculum-map__legend">
		<li>
			<span className="curriculum-map__key curriculum-map__key--mastered" aria-hidden="true" />
			Mastered
		</li>
		<li>
			<span className="curriculum-map__key curriculum-map__key--asked" aria-hidden="true" />
			Asked now, with your level
		</li>
		<li>
			<span className="curriculum-map__key curriculum-map__key--later" aria-hidden="true" />
			Coming later
		</li>
	</ul>
)

interface ConceptCardProps {
	map: ConceptMap
	concept: MapConcept
	/** Set when the card labels a dialog. */
	nameId?: string
}

const ConceptCard = ({ map, concept, nameId }: ConceptCardProps) => {
	const strand = map.strands.find(s => s.key === concept.strand)
	const before = buildsOn(map, concept.key)
	return (
		<div className="curriculum-map__card" aria-live={nameId === undefined ? 'polite' : undefined}>
			<p id={nameId} className="curriculum-map__card-name">
				{concept.name}
			</p>
			<p className="curriculum-map__card-where">
				{strand?.name} · Tier {concept.tier}, {map.tiers[concept.tier]}
			</p>
			<p className="curriculum-map__card-level">
				{levelText(concept)}
				{concept.mastery !== null && (
					<span className="curriculum-map__percent"> {percent(concept.mastery)}%</span>
				)}
			</p>
			<p className="curriculum-map__card-objective">{concept.objective}</p>
			{before.length > 0 && (
				<p className="curriculum-map__card-builds">
					Builds on {before.map(c => c.name).join(' ← ')}
					{before.some(c => !c.askable) && '. Those coming later count as met for now.'}
				</p>
			)}
		</div>
	)
}

interface ConceptDialogProps {
	map: ConceptMap
	concept: MapConcept
	onClose: () => void
}

/** A concept's card as a modal, closed by its button, Esc, or a click outside it. */
const ConceptDialog = ({ map, concept, onClose }: ConceptDialogProps) => {
	const dialog = useRef<HTMLDialogElement>(null)
	const nameId = useId()

	useEffect(() => {
		dialog.current?.showModal()
	}, [])

	const close = () => {
		dialog.current?.close()
	}
	return (
		<dialog
			ref={dialog}
			className="curriculum-map__dialog"
			aria-labelledby={nameId}
			onClose={onClose}
			onKeyDown={event => {
				// Esc here closes only the dialog, not the map underneath.
				if (event.key === 'Escape') event.stopPropagation()
			}}
			onClick={event => {
				if (event.target === event.currentTarget) close()
			}}>
			<ConceptCard map={map} concept={concept} nameId={nameId} />
			<button type="button" className="text-button curriculum-map__dialog-close" onClick={close}>
				Close
			</button>
		</dialog>
	)
}

export default CurriculumMap
