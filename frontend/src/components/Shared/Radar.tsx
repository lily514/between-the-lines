import type { Report } from '../../api/client.ts'
import { percent } from './ProgressBar.support.ts'
import { axes, RADIUS, RINGS, shape } from './Radar.support.ts'
import './Radar.css'

export interface RadarProps {
	strands: Report['strands']
	/** What "now" is: "Halftime" or "Full time". */
	nowLabel: string
}

/** The scouting report's radar: one axis per strand, kick-off dashed and now solid.
 *
 * A strand with nothing asked about yet has a dashed axis, "Not yet" and no point, never a zero. A table with the
 * same values is there for screen readers. */
const Radar = ({ strands, nowLabel }: RadarProps) => {
	const list = axes(strands)
	const pad = 30
	const size = RADIUS + pad
	const kickoff = shape(list, strand => strand.kickoff)
	const now = shape(list, strand => strand.now)
	return (
		<figure className="radar">
			<svg
				viewBox={`${String(-size)} ${String(-size)} ${String(size * 2)} ${String(size * 2)}`}
				className="radar__svg"
				aria-hidden="true">
				{RINGS.map(ring => (
					<polygon
						key={ring}
						className="radar__ring"
						points={list
							.map(axis => `${String(axis.dx * RADIUS * ring)},${String(axis.dy * RADIUS * ring)}`)
							.join(' ')}
					/>
				))}
				{list.map(axis => (
					<line
						key={axis.strand.key}
						x1={0}
						y1={0}
						x2={axis.dx * RADIUS}
						y2={axis.dy * RADIUS}
						className={axis.strand.now === null ? 'radar__axis radar__axis--empty' : 'radar__axis'}
					/>
				))}
				{kickoff !== '' && <polygon points={kickoff} className="radar__kickoff" />}
				{now !== '' && <polygon points={now} className="radar__now" />}
				{list.map(axis =>
					axis.strand.now === null ? null : (
						<circle
							key={axis.strand.key}
							cx={axis.dx * RADIUS * axis.strand.now}
							cy={axis.dy * RADIUS * axis.strand.now}
							r={1.6}
							className="radar__node"
						/>
					)
				)}
				{list.map(axis => {
					const x = axis.dx * (RADIUS + 4)
					const y = axis.dy * (RADIUS + 5) + (axis.dy < 0 ? -5 : axis.dy > 0 ? 3 : -1.5)
					const anchor = axis.dx > 0 ? 'start' : axis.dx < 0 ? 'end' : 'middle'
					return (
						<text key={axis.strand.key} x={x} y={y} textAnchor={anchor} className="radar__label">
							<tspan>{axis.strand.name}</tspan>
							<tspan
								x={x}
								dy={5.8}
								className={axis.strand.now === null ? 'radar__empty' : 'radar__value'}>
								{axis.strand.now === null ? 'Not yet' : `${String(percent(axis.strand.now))}%`}
							</tspan>
						</text>
					)
				})}
			</svg>
			<figcaption className="radar__key">
				<span>
					<span className="radar__swatch radar__swatch--now" aria-hidden="true" />
					{nowLabel}
				</span>
				<span>
					<span className="radar__swatch radar__swatch--kickoff" aria-hidden="true" />
					Kick-off
				</span>
			</figcaption>
			<table className="visually-hidden">
				<caption>Your scouting report by strand</caption>
				<thead>
					<tr>
						<th scope="col">Strand</th>
						<th scope="col">Kick-off</th>
						<th scope="col">{nowLabel}</th>
					</tr>
				</thead>
				<tbody>
					{list.map(axis => (
						<tr key={axis.strand.key}>
							<th scope="row">{axis.strand.name}</th>
							<td>
								{axis.strand.kickoff === null ? 'Not yet' : `${String(percent(axis.strand.kickoff))}%`}
							</td>
							<td>{axis.strand.now === null ? 'Not yet' : `${String(percent(axis.strand.now))}%`}</td>
						</tr>
					))}
				</tbody>
			</table>
		</figure>
	)
}

export default Radar
