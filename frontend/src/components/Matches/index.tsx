import { useEffect, useId, useRef } from 'react'
import type { MatchSummary, Status } from '../../api/client.ts'
import Crest from '../Shared/Crest.tsx'
import StartOver from '../Shared/StartOver.tsx'
import './index.css'

export interface MatchesProps {
	status: Status
	matches: MatchSummary[]
	/** See who's playing in the next match, then kick off. */
	onWatch: () => void
	/** Carry on with the match part-way through, at the question waiting. */
	onRejoin: () => void
	/** Go back to the club picker; only offered while the viewer can still change their team. */
	onChangeTeam: () => void
	onStartOver: () => void
}

/** Home base: the viewer's matches, the one to watch next, and the one to rejoin. */
const Matches = ({ status, matches, onWatch, onRejoin, onChangeTeam, onStartOver }: MatchesProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="matches" aria-labelledby={headingId}>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="matches__heading screen-heading">
				Matches
			</h2>
			{status.club !== null && (
				<p className="matches__team">
					<Crest code={status.club.code} size={24} />
					<span>
						Your team: <strong>{status.club.name}</strong>
					</span>
					{status.can_choose_club && (
						<button type="button" className="text-button" onClick={onChangeTeam}>
							Change
						</button>
					)}
				</p>
			)}
			<ul className="matches__list">
				{matches.map(match => (
					<li key={match.match_number} className="matches__match">
						<p className="matches__when">
							Matchday {match.matchday} · {match.date_label} · {match.kick_off}
						</p>
						<p className="matches__fixture">
							{match.home} v {match.away}
						</p>
						{match.state === 'in_progress' && (
							<button type="button" className="primary-button" onClick={onRejoin}>
								Rejoin the match
							</button>
						)}
						{match.state === 'upcoming' && match.match_number === status.match_number && (
							<button type="button" className="primary-button" onClick={onWatch}>
								See who’s playing
							</button>
						)}
					</li>
				))}
			</ul>
			<div className="matches__start-over">
				<StartOver
					label={status.finished ? 'Start again with new matches' : 'Start over'}
					onConfirm={onStartOver}
				/>
			</div>
		</section>
	)
}

export default Matches
