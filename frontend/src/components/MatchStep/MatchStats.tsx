import type { Stats, Teams } from './Commentary.support.ts'
import SideMark from './SideMark.tsx'
import './MatchStats.css'

export interface MatchStatsProps {
	stats: Stats
	teams: Teams
}

type Count = Exclude<keyof Stats['home'], 'possession' | 'goals'>

const COUNTS: { key: Count; label: string }[] = [
	{ key: 'attempts', label: 'Shots' },
	{ key: 'corners', label: 'Corners' },
	{ key: 'fouls', label: 'Fouls' },
	{ key: 'yellow_cards', label: 'Yellow cards' }
]

/** The match's numbers so far as cards, home on the left and away on the right, as the server counted them. A red
 * card shows only once there is one. */
const MatchStats = ({ stats, teams }: MatchStatsProps) => {
	const counts =
		stats.home.red_cards + stats.away.red_cards > 0
			? [...COUNTS, { key: 'red_cards' as const, label: 'Red cards' }]
			: COUNTS
	return (
		<ul className="match-stats" aria-label="Match stats">
			{counts.map(count => (
				<li key={count.key} className="match-stats__card">
					<span className="match-stats__label">{count.label}</span>
					<span className="match-stats__values">
						<span className="match-stats__value">
							<SideMark side="home" />
							<span className="visually-hidden">{teams.homeCode} </span>
							{stats.home[count.key]}
						</span>
						<span className="match-stats__value">
							<span className="visually-hidden">{teams.awayCode} </span>
							{stats.away[count.key]}
							<SideMark side="away" />
						</span>
					</span>
				</li>
			))}
		</ul>
	)
}

export default MatchStats
