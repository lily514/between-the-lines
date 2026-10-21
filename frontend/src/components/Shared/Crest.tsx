import crests from '../../assets/crests.svg?no-inline'
import './Crest.css'

export interface CrestProps {
	/** The club's three-letter code, as the API sends it. */
	code: string
	size: number
}

/** A club's crest. It is decoration: the club's name is always shown beside it. */
const Crest = ({ code, size }: CrestProps) => (
	<svg className="crest" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
		<use href={`${crests}#crest-${code}`} />
	</svg>
)

export default Crest
