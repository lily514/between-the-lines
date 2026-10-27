import { MARKINGS } from './index.support.ts'

/** The pitch's lines and spots over the whole pitch, in screen metres. */
const Markings = () => (
	<g className="pitch__markings">
		<rect {...MARKINGS.outline} />
		<line x1={0} y1={MARKINGS.halfway} x2={MARKINGS.outline.width} y2={MARKINGS.halfway} />
		<circle cx={MARKINGS.centre.x} cy={MARKINGS.centre.y} r={MARKINGS.centre.r} />
		{MARKINGS.boxes.map(box => (
			<rect key={`${String(box.y)}-${String(box.width)}`} {...box} />
		))}
		{MARKINGS.spots.map(([x, y]) => (
			<circle key={y} className="pitch__spot" cx={x} cy={y} r={0.3} />
		))}
	</g>
)

export default Markings
