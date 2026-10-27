import { useEffect, useId, useRef } from 'react'
import type { MatchSummary, Status } from '../../api/client.ts'
import Crest from '../Shared/Crest.tsx'
import LevelWord from '../Shared/LevelWord.tsx'
import StartOver from '../Shared/StartOver.tsx'
import { featured, scoreLine } from './index.support.ts'
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
	/** Open the curriculum map. */
	onMap: () => void
	/** Open a finished match's full-time report. */
	onReport: (matchNumber: number) => void
	onStartOver: () => void
}

/** Home base: the match to rejoin or watch next, the viewer's progress on what is asked now, and earlier matches. */
const Matches = ({ status, matches, onWatch, onRejoin, onChangeTeam, onMap, onReport, onStartOver }: MatchesProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const progressId = useId()
	const earlierId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	const current = featured(matches)
	const earlier = matches.filter(match => match.state === 'finished')
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
			{current?.state === 'in_progress' && (
				<section className="matches__card matches__card--now" aria-label="Match part-way through">
					<p className="matches__label matches__label--now">
						<span>Part-way through · Matchday {current.matchday}</span>
						{current.score?.clock != null && (
							<span className="matches__clock">at {current.score.clock}</span>
						)}
					</p>
					<Fixture match={current} middle={current.score === null ? 'v' : scoreLine(current.score)} />
					<p className="matches__note">
						<span className="matches__number">{current.questions}</span>{' '}
						{current.questions === 1 ? 'question' : 'questions'} answered. The match waits for you.
					</p>
					<button type="button" className="primary-button" onClick={onRejoin}>
						Rejoin the match
					</button>
				</section>
			)}
			{current?.state === 'upcoming' && (
				<section className="matches__card" aria-label="Next match">
					<p className="matches__label">Next match · Matchday {current.matchday}</p>
					<Fixture match={current} middle="v" />
					<p className="matches__when">
						{current.date_label} · kick-off <span className="matches__number">{current.kick_off}</span>
					</p>
					<p className="matches__note">
						The match moves on one moment at a time, and waits while you answer.
					</p>
					<button type="button" className="primary-button" onClick={onWatch}>
						See who’s playing
					</button>
				</section>
			)}
			{current === null && (
				<section className="matches__card" aria-label="Season">
					<p className="matches__label">All {matches.length} matches watched</p>
					<p className="matches__note">Your reports are below. Start again for new matches.</p>
				</section>
			)}
			<section className="matches__card matches__card--plain" aria-labelledby={progressId}>
				<div className="matches__section-head">
					<h3 id={progressId} className="matches__section">
						Your progress
					</h3>
					<span className="matches__aside">{status.concepts.length} concepts asked now</span>
				</div>
				<ul className="matches__progress">
					{status.concepts.map(concept => (
						<li key={concept.name}>
							<span>{concept.name}</span>
							<span className="matches__level">
								<LevelWord
									level={concept.level}
									band={concept.band}
									mastered={concept.value >= status.thresholds.mastery}
									waitsFor={concept.waits_for}
								/>
							</span>
						</li>
					))}
				</ul>
				<button type="button" className="text-button matches__map" onClick={onMap}>
					See your full map
				</button>
			</section>
			{earlier.length > 0 && (
				<section aria-labelledby={earlierId}>
					<h3 id={earlierId} className="matches__section">
						Earlier
					</h3>
					<ul className="matches__earlier">
						{earlier.map(match => (
							<li key={match.match_number}>
								<span className="matches__when">Matchday {match.matchday}</span>
								<span className="matches__result">
									{match.home} {match.score === null ? 'v' : scoreLine(match.score)} {match.away}
								</span>
								<button
									type="button"
									className="text-button matches__report"
									aria-label={`Report, matchday ${String(match.matchday)}`}
									onClick={() => {
										onReport(match.match_number)
									}}>
									Report
								</button>
							</li>
						))}
					</ul>
				</section>
			)}
			<div className="matches__start-over">
				<StartOver
					label={status.finished ? 'Start again with new matches' : 'Start over'}
					onConfirm={onStartOver}
				/>
			</div>
		</section>
	)
}

/** The two clubs either side of the score (or "v"): crest, name, Home or Away, and "You" on the viewer's team. */
const Fixture = ({ match, middle }: { match: MatchSummary; middle: string }) => (
	<div className="matches__fixture">
		<Side name={match.home} code={match.home_code} where="Home" yours={match.your_team === 'home'} />
		<span className={middle === 'v' ? 'matches__versus' : 'matches__score'}>{middle}</span>
		<Side name={match.away} code={match.away_code} where="Away" yours={match.your_team === 'away'} end />
	</div>
)

interface SideProps {
	name: string
	code: string
	where: 'Home' | 'Away'
	yours: boolean
	end?: boolean
}

const Side = ({ name, code, where, yours, end = false }: SideProps) => (
	<div className={end ? 'matches__side matches__side--end' : 'matches__side'}>
		<span className="matches__club">
			<Crest code={code} size={24} />
			<span className="matches__name">{name}</span>
		</span>
		<span className="matches__where">
			{where}
			{yours && <span className="matches__you">You</span>}
		</span>
	</div>
)

export default Matches
