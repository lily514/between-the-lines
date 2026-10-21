import type { CSSProperties } from 'react'
import type { SheetPlayer, SheetTeam } from '../../api/client.ts'
import Crest from '../Shared/Crest.tsx'
import './TeamCard.css'
import { groupsOf, watchedLine } from './index.support.ts'

export interface TeamCardProps {
	team: SheetTeam
	/** From stage 2, positions also show their abbreviation. */
	abbreviated: boolean
	/** From stage 3, each player shows their numbers from watched matches, or that they haven't been seen yet. */
	counted: boolean
}

/** One side on the team sheet: the club, then its starters by position group. */
const TeamCard = ({ team, abbreviated, counted }: TeamCardProps) => {
	const line = watchedLine(team)
	const colour = { '--club': `var(--club-${team.code})` } as CSSProperties
	return (
		<article
			className={`team-card${team.yours ? ' team-card--yours' : ''}`}
			style={colour}
			aria-labelledby={`team-${team.code}`}>
			<header className="team-card__header">
				<Crest code={team.code} size={48} />
				<div className="team-card__title">
					<h3 id={`team-${team.code}`} className="team-card__name">
						{team.name}
						{team.yours && <span className="team-card__you">You</span>}
					</h3>
					<p className="team-card__meta">
						<span className="team-card__code">{team.code}</span> ·{' '}
						{team.home ? 'Home · filled discs' : 'Away · rings'}
						{team.formation !== null && (
							<>
								{' · '}
								<span className="team-card__formation">{team.formation}</span>
							</>
						)}
					</p>
				</div>
			</header>
			{groupsOf(team).map(group => (
				<section key={group.heading} className="team-card__group" aria-label={`${team.name}: ${group.heading}`}>
					<h4 className="team-card__group-heading">{group.heading}</h4>
					<ul className="team-card__players">
						{group.players.map(player => (
							<PlayerRow
								key={player.shirt}
								player={player}
								home={team.home}
								abbreviated={abbreviated}
								counted={counted}
							/>
						))}
					</ul>
				</section>
			))}
			{line !== null && <p className="team-card__watched">{line}</p>}
		</article>
	)
}

interface PlayerRowProps {
	player: SheetPlayer
	home: boolean
	abbreviated: boolean
	counted: boolean
}

const PlayerRow = ({ player, home, abbreviated, counted }: PlayerRowProps) => {
	const numbers = player.numbers
	return (
		<li className="team-card__player">
			<span
				className={`team-card__shirt team-card__shirt--${home ? 'home' : 'away'}`}
				aria-label={`Number ${String(player.shirt)}`}>
				{player.shirt}
			</span>
			<div className="team-card__who">
				<p className="team-card__player-name">{player.name}</p>
				<p className="team-card__position">
					{abbreviated && (
						<>
							<abbr className="team-card__short" title={player.position.name}>
								{player.position.short}
							</abbr>{' '}
						</>
					)}
					<span className="team-card__position-name">{player.position.name}</span>:{' '}
					{player.position.description}
				</p>
				{counted && numbers === null && <p className="team-card__unseen">First time you've seen them</p>}
				{counted && numbers !== null && (
					<dl className="team-card__numbers">
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
							<dd className="team-card__threat">{numbers.threat_added.display}</dd>
						</div>
					</dl>
				)}
			</div>
		</li>
	)
}

export default TeamCard
