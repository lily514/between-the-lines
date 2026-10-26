import type { SheetTeam } from '../../api/client.ts'
import './LineupList.css'
import { shirtName, spotLabel, type Spot } from './index.support.ts'

export interface LineupListProps {
	teams: readonly SheetTeam[]
	spots: readonly Spot[]
	chosen: Spot | undefined
	/** From stage 2, each row shows the position's tag. */
	abbreviated: boolean
	onChoose: (key: string) => void
}

/** Both elevens as plain buttons, collapsed: the same choice as tapping a player on the pitch. */
const LineupList = ({ teams, spots, chosen, abbreviated, onChoose }: LineupListProps) => (
	<details className="lineup-list">
		<summary className="lineup-list__summary">Both line-ups as a list</summary>
		{teams.map(team => (
			<section key={team.code} className="lineup-list__team" aria-labelledby={`lineup-${team.code}`}>
				<h3 id={`lineup-${team.code}`} className="lineup-list__heading">
					{team.name}
				</h3>
				<ul className="lineup-list__players">
					{spots
						.filter(spot => spot.team === team)
						.map(spot => (
							<li key={spot.key}>
								<button
									type="button"
									className="lineup-list__player"
									aria-label={spotLabel(spot)}
									aria-pressed={spot.key === chosen?.key}
									onClick={() => {
										onChoose(spot.key)
									}}>
									<span className="lineup-list__shirt">{spot.player.shirt}</span>
									<span className="lineup-list__name">{shirtName(spot.player)}</span>
									{abbreviated && (
										<span className="lineup-list__tag">{spot.player.position.short}</span>
									)}
								</button>
							</li>
						))}
				</ul>
			</section>
		))}
	</details>
)

export default LineupList
