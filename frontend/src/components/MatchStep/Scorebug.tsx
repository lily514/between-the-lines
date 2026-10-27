import Crest from '../Shared/Crest.tsx'
import { codeOf, halfWord, type Side, type Stats, type Teams } from './Commentary.support.ts'
import SideMark from './SideMark.tsx'
import './Scorebug.css'

export interface ScorebugProps {
	teams: Teams
	/** The match's numbers as they stand, for the score, the half and possession; null before the first. */
	stats: Stats | null
	/** The match clock, e.g. 00:29. */
	clock: string
	/** How long until the next question, or that it is question time. */
	countdown: string
	/** The phone's one-row version, without crests or names. */
	compact?: boolean
}

/** The score, the clock and possession, with each club's crest, code and mark, and "You" on the viewer's club. */
const Scorebug = ({ teams, stats, clock, countdown, compact = false }: ScorebugProps) => {
	const home = stats?.home.goals ?? 0
	const away = stats?.away.goals ?? 0
	const half = halfWord(stats?.period ?? 1)
	return (
		<section
			className={compact ? 'scorebug scorebug--compact' : 'scorebug'}
			aria-label="Score, clock and possession">
			<div className="scorebug__row">
				<Team teams={teams} side="home" compact={compact} />
				<div className="scorebug__middle">
					<div className="scorebug__score" aria-label={`Score ${String(home)} to ${String(away)}`}>
						<span>{home}</span>
						<span className="scorebug__dash" aria-hidden="true">
							–
						</span>
						<span>{away}</span>
					</div>
					<div className="scorebug__clock">
						<span className="scorebug__time" role="timer" aria-label="Match clock">
							{clock}
						</span>
						<span className="scorebug__half">{half}</span>
					</div>
					<span className="scorebug__countdown">{countdown}</span>
				</div>
				<Team teams={teams} side="away" compact={compact} />
			</div>
			{stats !== null && <Possession teams={teams} stats={stats} />}
		</section>
	)
}

const Team = ({ teams, side, compact }: { teams: Teams; side: Side; compact: boolean }) => {
	const code = codeOf(teams, side)
	const yours = teams.yours === side
	const name = side === 'home' ? teams.home : teams.away
	return (
		<div className={`scorebug__team scorebug__team--${side}${yours ? ' scorebug__team--yours' : ''}`}>
			{compact && <span className="visually-hidden">{`${name}, ${side}`}</span>}
			<div className="scorebug__badges">
				{!compact && <Crest code={code} size={48} />}
				{yours && <span className="scorebug__you">You</span>}
				<span className="scorebug__code">{code}</span>
				{compact && <SideMark side={side} />}
			</div>
			{!compact && (
				<>
					<span className="scorebug__name">{name}</span>
					<span className="scorebug__legend">
						{side === 'home' ? 'Home · filled discs' : 'Away · rings'}
						<SideMark side={side} />
					</span>
				</>
			)}
		</div>
	)
}

const Possession = ({ teams, stats }: { teams: Teams; stats: Stats }) => (
	<div className="scorebug__possession">
		<div className="scorebug__possession-numbers">
			<span>
				{stats.home.possession}% <span className="scorebug__possession-code">{teams.homeCode}</span>
			</span>
			<span className="scorebug__possession-label">Possession</span>
			<span>
				<span className="scorebug__possession-code">{teams.awayCode}</span> {stats.away.possession}%
			</span>
		</div>
		<div
			className="scorebug__bar"
			role="img"
			aria-label={`Possession: ${teams.home} ${String(stats.home.possession)}%, ${teams.away} ${String(stats.away.possession)}%`}>
			<span className="scorebug__bar-home" style={{ width: `${String(stats.home.possession)}%` }} />
			<span className="scorebug__bar-away" />
		</div>
	</div>
)

export default Scorebug
