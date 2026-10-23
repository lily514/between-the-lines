import { useEffect, useId, useRef, useState } from 'react'
import type { TeamSheet as TeamSheetData } from '../../api/client.ts'
import ClubCard from './ClubCard.tsx'
import './index.css'
import { firstPick, spotsOf } from './index.support.ts'
import KickoffPitch from './KickoffPitch.tsx'
import LineupList from './LineupList.tsx'
import PlayerCard from './PlayerCard.tsx'

export interface TeamSheetProps {
	sheet: TeamSheetData
	/** Whether the viewer can still change their team, which offers a way back to the picker. */
	canChangeTeam: boolean
	onKickOff: () => void
	onChangeTeam: () => void
}

/** Who's playing, before each match: both elevens on the kick-off pitch, the viewer's team attacking up. Choosing a
 * player fills the card under the pitch, which grows with the viewer's level. */
const TeamSheet = ({ sheet, canChangeTeam, onKickOff, onChangeTeam }: TeamSheetProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const spots = spotsOf(sheet)
	const [chosenKey, setChosenKey] = useState(() => firstPick(spots)?.key)
	const chosen = spots.find(spot => spot.key === chosenKey)
	const abbreviated = sheet.stage >= 2
	const counted = sheet.stage >= 3

	useEffect(() => {
		heading.current?.focus()
	}, [])

	return (
		<section className="team-sheet" aria-labelledby={headingId}>
			<p className="team-sheet__eyebrow">
				Before kick-off · Match <span className="team-sheet__number">{sheet.match_number}</span>
			</p>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="team-sheet__heading screen-heading">
				Who's playing
			</h2>
			<div className="team-sheet__clubs">
				{sheet.teams.map(team => (
					<ClubCard key={team.code} team={team} />
				))}
			</div>
			<figure className="team-sheet__pitch">
				<div className="team-sheet__pitch-head">
					<h3 className="team-sheet__pitch-heading">Kick-off positions</h3>
					<span className="team-sheet__hint team-sheet__hint--touch">Tap a player</span>
					<span className="team-sheet__hint team-sheet__hint--pointer">Hover or click a player</span>
				</div>
				<KickoffPitch
					sheet={sheet}
					spots={spots}
					chosen={chosen}
					abbreviated={abbreviated}
					onChoose={setChosenKey}
				/>
				<figcaption className="team-sheet__key">
					<span>
						<span className="team-sheet__glyph team-sheet__glyph--home" aria-hidden="true" />
						Home
					</span>
					<span>
						<span className="team-sheet__glyph team-sheet__glyph--away" aria-hidden="true" />
						Away
					</span>
					{sheet.teams.some(team => team.yours) && (
						<span>
							<span className="team-sheet__glyph team-sheet__glyph--yours" aria-hidden="true" />
							Your team
						</span>
					)}
					<span>Numbers are shirt numbers</span>
				</figcaption>
			</figure>
			{chosen !== undefined && <PlayerCard spot={chosen} abbreviated={abbreviated} counted={counted} />}
			<LineupList
				teams={sheet.teams}
				spots={spots}
				chosen={chosen}
				abbreviated={abbreviated}
				onChoose={setChosenKey}
			/>
			{sheet.next_stage !== null && (
				<p className="team-sheet__next">
					<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
						<rect x="5" y="11" width="14" height="10" rx="2" />
						<path d="M8 11V8a4 4 0 0 1 8 0v3" />
					</svg>
					{sheet.next_stage}
				</p>
			)}
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
