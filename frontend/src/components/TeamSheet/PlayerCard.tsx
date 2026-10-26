import './PlayerCard.css'
import { teamWords, watchedLine, type Spot } from './index.support.ts'

export interface PlayerCardProps {
	spot: Spot
	/** From stage 2, the card shows the position's tag. */
	abbreviated: boolean
	/** From stage 3, the card shows the player's numbers from watched matches, or that they haven't been seen. */
	counted: boolean
}

/** The chosen player: who they are, their position in words and, as the viewer grows, their numbers. */
const PlayerCard = ({ spot, abbreviated, counted }: PlayerCardProps) => {
	const { player, team } = spot
	const numbers = player.numbers
	const line = counted ? watchedLine(team) : null
	return (
		<section className="player-card" aria-live="polite" aria-label="Chosen player">
			<header className="player-card__header">
				<span
					className={`player-card__shirt player-card__shirt--${team.home ? 'home' : 'away'}`}
					aria-hidden="true">
					{player.shirt}
				</span>
				<div className="player-card__who">
					<h3 className="player-card__name">{player.name}</h3>
					<p className="player-card__team">
						<span className="visually-hidden">Number {player.shirt}, </span>
						{teamWords(team)}
					</p>
				</div>
				{abbreviated && (
					<abbr className="player-card__tag" title={player.position.name}>
						{player.position.short}
					</abbr>
				)}
			</header>
			<p className="player-card__position">
				<span className="player-card__position-name">{player.position.name}</span>{' '}
				<span className="player-card__description">{player.position.description}</span>
			</p>
			{counted && numbers === null && (
				<p className="player-card__unseen">
					<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
						<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
						<circle cx="12" cy="12" r="3" />
					</svg>
					First time you've seen them
				</p>
			)}
			{counted && numbers !== null && (
				<dl className="player-card__numbers">
					<div>
						<dt>Matches watched</dt>
						<dd>{numbers.matches}</dd>
					</div>
					<div>
						<dt>Passes completed</dt>
						<dd>
							{numbers.passes_completed}/{numbers.passes_tried}
						</dd>
					</div>
					<div>
						<dt>Line-breaking passes</dt>
						<dd>{numbers.line_breaking_passes}</dd>
					</div>
					<div>
						<dt>Threat added</dt>
						<dd className="player-card__threat">{numbers.threat_added.display}</dd>
					</div>
				</dl>
			)}
			{line !== null && <p className="player-card__watched">{line}</p>}
		</section>
	)
}

export default PlayerCard
