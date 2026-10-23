import { useEffect, useId, useRef } from 'react'
import type { ConceptMap } from '../../api/client.ts'
import './index.css'

export interface CurriculumMapProps {
	/** The map; null while it loads. */
	map: ConceptMap | null
	error: string | null
	/** Close the map and go back to the screen underneath, as it was. */
	onBack: () => void
}

/** Every concept there is to learn, by strand and tier, with the viewer's level on those asked about now.
 *
 * It opens over whatever screen the viewer was on; Back or Esc closes it. */
const CurriculumMap = ({ map, error, onBack }: CurriculumMapProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	useEffect(() => {
		const close = (event: KeyboardEvent) => {
			if (event.key === 'Escape') onBack()
		}
		document.addEventListener('keydown', close)
		return () => {
			document.removeEventListener('keydown', close)
		}
	}, [onBack])

	return (
		<section className="curriculum-map" aria-labelledby={headingId}>
			<button
				type="button"
				className="text-button curriculum-map__back"
				aria-label="Close the map and go back to where you were"
				onClick={onBack}>
				← Back
			</button>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="curriculum-map__heading screen-heading">
				Your map
			</h2>
			{error !== null && (
				<p className="curriculum-map__error" role="alert">
					{error}
				</p>
			)}
			{map === null && error === null && <p role="status">Finding the map…</p>}
			{map?.strands.map(strand => (
				<section key={strand.key} aria-label={strand.name} className="curriculum-map__strand">
					<h3 className="curriculum-map__strand-name">{strand.name}</h3>
					<ul className="curriculum-map__concepts">
						{map.concepts
							.filter(concept => concept.strand === strand.key)
							.map(concept => (
								<li key={concept.key}>
									<span>{concept.name}</span>{' '}
									<span className="curriculum-map__level">
										{concept.askable ? (concept.level ?? 'Asked now') : 'Coming later'}
									</span>
								</li>
							))}
					</ul>
				</section>
			))}
		</section>
	)
}

export default CurriculumMap
