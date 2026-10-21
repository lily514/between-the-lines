import { useEffect, useId, useRef } from 'react'
import type { TeamSheet as TeamSheetData } from '../../api/client.ts'
import Pitch from '../Shared/Pitch/index.tsx'
import './index.css'
import { kickoffPicture, yourSide } from './index.support.ts'
import TeamCard from './TeamCard.tsx'

export interface TeamSheetProps {
	sheet: TeamSheetData
	/** Whether the viewer can still change their team, which offers a way back to the picker. */
	canChangeTeam: boolean
	onKickOff: () => void
	onChangeTeam: () => void
}

/** Who's playing, before each match: the viewer's team first, growing with the viewer's level. */
const TeamSheet = ({ sheet, canChangeTeam, onKickOff, onChangeTeam }: TeamSheetProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const side = yourSide(sheet)
	const picture = kickoffPicture(sheet)
	const home = sheet.teams.find(team => team.home)
	const away = sheet.teams.find(team => !team.home)

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="team-sheet" aria-labelledby={headingId}>
			<p className="team-sheet__eyebrow">Before kick-off</p>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="team-sheet__heading screen-heading">
				Who's playing
			</h2>
			{home !== undefined && away !== undefined && (
				<p className="team-sheet__fixture">
					Match <span className="team-sheet__number">{sheet.match_number}</span> · {home.name} (home) v{' '}
					{away.name} (away)
				</p>
			)}
			<ul className="team-sheet__key" aria-label="Key">
				<li>
					<span className="team-sheet__glyph team-sheet__glyph--home" aria-hidden="true">
						7
					</span>
					Filled disc: home side
				</li>
				<li>
					<span className="team-sheet__glyph team-sheet__glyph--away" aria-hidden="true">
						7
					</span>
					Ring: away side
				</li>
				{side !== null && (
					<li>
						<span className="team-sheet__glyph team-sheet__glyph--yours" aria-hidden="true">
							You
						</span>
						Dashed ring and "You": your team
					</li>
				)}
				<li>
					<span className="team-sheet__glyph team-sheet__glyph--hash" aria-hidden="true">
						#
					</span>
					Numbers are shirt numbers
				</li>
			</ul>
			{picture !== null && (
				// The lists below say the same, so screen readers skip the picture.
				<figure className="team-sheet__pitch" aria-hidden="true">
					<figcaption className="team-sheet__pitch-caption">
						Kick-off shape{side !== null && ': your team attacks up'}
					</figcaption>
					<Pitch picture={picture} label="Kick-off" yours={side} ball={false} />
				</figure>
			)}
			<div className="team-sheet__teams">
				{sheet.teams.map(team => (
					<TeamCard key={team.code} team={team} abbreviated={sheet.stage >= 2} counted={sheet.stage >= 3} />
				))}
			</div>
			{sheet.next_stage !== null && <p className="team-sheet__next">{sheet.next_stage}</p>}
			<button type="button" className="primary-button" onClick={onKickOff}>
				Kick off
			</button>
			{canChangeTeam && (
				<button type="button" className="text-button team-sheet__change" onClick={onChangeTeam}>
					Not your team? Change it
				</button>
			)}
		</section>
	)
}

export default TeamSheet
