import './StatTile.css'

export interface StatTileProps {
	label: string
	/** The fact's display text from the evidence pack, shown exactly as sent. */
	value: string
	unit?: string
}

/** One measured fact: a label, then its value in the data font. Sits inside a `<dl>`. */
const StatTile = ({ label, value, unit }: StatTileProps) => (
	<div className="stat-tile">
		<dt className="stat-tile__label">{label}</dt>
		<dd className="stat-tile__value">
			{value}
			{unit !== undefined && <span className="stat-tile__unit"> {unit}</span>}
		</dd>
	</div>
)

export default StatTile
