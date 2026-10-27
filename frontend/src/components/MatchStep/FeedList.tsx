import { useId, type ReactNode } from 'react'
import { codeOf, matchClock, type FeedEntry, type Teams } from './Commentary.support.ts'
import SideMark from './SideMark.tsx'
import './FeedList.css'

export interface FeedListProps {
	/** The feed so far, newest first. */
	entries: FeedEntry[]
	teams: Teams
	/** The heading's level: 2 in the stream view, 3 inside the phone's sheet. */
	level?: 2 | 3
}

/** The match feed, newest first: each row its time, its team's mark and code, and the event in words. It runs from
 * kick-off, so it ends at the start of the match. */
const FeedList = ({ entries, teams, level = 2 }: FeedListProps) => {
	const headingId = useId()
	const Heading = level === 2 ? 'h2' : 'h3'
	return (
		<section className="feed-list" aria-labelledby={headingId}>
			<div className="feed-list__head">
				<Heading id={headingId} className="feed-list__heading">
					Match feed
				</Heading>
				<span className="feed-list__order">Newest first</span>
			</div>
			<ol className="feed-list__entries">
				{entries.map(entry => (
					<Entry key={`${entry.kind}-${String(entry.at)}-${entry.label}`} entry={entry} teams={teams} />
				))}
			</ol>
			<p className="feed-list__start">Start of the match</p>
		</section>
	)
}

const Entry = ({ entry, teams }: { entry: FeedEntry; teams: Teams }) => {
	const clock = matchClock(entry.at)
	const score =
		entry.score === null
			? null
			: `${teams.homeCode} ${String(entry.score.home)} – ${String(entry.score.away)} ${teams.awayCode}`
	if (entry.kind === 'halftime') {
		return (
			<li className="feed-list__halftime">
				<span className="feed-list__rule" aria-hidden="true" />
				<span className="feed-list__meta">
					<FeedIcon kind="halftime" />
					{entry.label}
				</span>
				{score !== null && <span className="feed-list__score">{score}</span>}
				<span className="feed-list__rule" aria-hidden="true" />
			</li>
		)
	}
	const team: ReactNode =
		entry.side === null ? null : (
			<>
				<SideMark side={entry.side} />
				{codeOf(teams, entry.side)}
			</>
		)
	const move = entry.kind === 'move'
	return (
		<li className={`feed-list__entry${entry.kind === 'goal' ? ' feed-list__entry--goal' : ''}`}>
			<span className="feed-list__clock">{clock}</span>
			<div className="feed-list__body">
				<span className="feed-list__meta">
					{move ? (
						<>
							{team} · {entry.label}
						</>
					) : (
						<>
							<FeedIcon kind={entry.kind} />
							{entry.label} · {team}
						</>
					)}
				</span>
				{entry.text !== '' && <span className="feed-list__text">{entry.text}</span>}
				{entry.names.length > 0 && <Names names={entry.names} />}
				{entry.kind === 'goal' && score !== null && <span className="feed-list__score">{score}</span>}
			</div>
		</li>
	)
}

const Names = ({ names }: { names: string[] }) => (
	<span className="feed-list__names">
		{names.map((name, i) => (
			<span key={`${name}-${String(i)}`}>
				{i > 0 && (
					<span className="feed-list__arrow" aria-label="to">
						{' → '}
					</span>
				)}
				{name}
			</span>
		))}
	</span>
)

/** Each kind of entry's icon, beside its words; a move has its team's mark instead. */
const FeedIcon = ({ kind }: { kind: FeedEntry['kind'] }) => (
	<svg className={`feed-list__icon feed-list__icon--${kind}`} viewBox="0 0 24 24" aria-hidden="true">
		{(kind === 'goal' || kind === 'own_goal') && <path d="M3 20V6h18v14M3 10h18M3 14h18M9 6v14M15 6v14" />}
		{kind === 'shot' && <path d="M9 15l11-11M14 4h6v6M3 18a3 3 0 1 0 6 0a3 3 0 1 0-6 0" />}
		{kind === 'corner' && <path d="M5 21V3l10 4-10 4" />}
		{(kind === 'throw_in' || kind === 'goal_kick') && <rect x="5" y="5" width="14" height="14" rx="1" />}
		{kind === 'foul' && <path d="M13 11l8-4M14 9h6M4 14a5 5 0 1 0 10 0a5 5 0 1 0-10 0" />}
		{(kind === 'yellow_card' || kind === 'red_card') && <rect x="6" y="3" width="12" height="18" rx="2" />}
		{kind === 'offside' && <path d="M5 21V4h10l-1.5 3.5L15 11H5" />}
		{kind === 'kick_off' && <path d="M3 12h18M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0" />}
		{kind === 'halftime' && <path d="M9 5v14M15 5v14" />}
	</svg>
)

export default FeedList
