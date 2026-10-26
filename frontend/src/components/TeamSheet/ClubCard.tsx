import type { SheetTeam } from '../../api/client.ts'
import './ClubCard.css'

export interface ClubCardProps {
	team: SheetTeam
}

/** One side, in short: its shape on the pitch, its name, home or away, and its formation from stage 2. */
const ClubCard = ({ team }: ClubCardProps) => (
	<article className={`club-card${team.yours ? ' club-card--yours' : ''}`} aria-labelledby={`club-${team.code}`}>
		<h3 id={`club-${team.code}`} className="club-card__name">
			<span className={`club-card__glyph club-card__glyph--${team.home ? 'home' : 'away'}`} aria-hidden="true" />
			{team.name}
		</h3>
		<p className="club-card__meta">
			{team.yours && <span className="club-card__you">You</span>}
			<span>
				{team.home ? 'Home' : 'Away'}
				<span className="visually-hidden">{team.home ? ', filled discs' : ', rings'}</span>
			</span>
			{team.formation !== null && <span className="club-card__formation">{team.formation}</span>}
		</p>
	</article>
)

export default ClubCard
