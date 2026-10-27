import { codeOf, type Side, type Teams, type Touch } from './Commentary.support.ts'
import SideMark from './SideMark.tsx'
import './NowCard.css'

export interface NowCardProps {
	teams: Teams
	clock: string
	/** Who is on the ball now; null before the first touch, and in play the play-by-play doesn't name. */
	onBall: { side: Side; touch: Touch } | null
	/** Whether the question is waiting in the panel. */
	asked: boolean
	/** The phone's caption, without the strip of thirds. */
	compact?: boolean
}

const THIRDS = [
	{ zones: ['own_third'], label: 'Own third' },
	{ zones: ['middle_third'], label: 'Midfield' },
	{ zones: ['final_third', 'box'], label: 'Final third' }
]

/** The latest action in large type: who has the ball and what they did with it, and where, as a strip of thirds
 * seen by the team on the ball. */
const NowCard = ({ teams, clock, onBall, asked, compact = false }: NowCardProps) => (
	<section className={compact ? 'now-card now-card--compact' : 'now-card'} aria-label="Latest action">
		<div className="now-card__top">
			<span className="now-card__now">
				<NowIcon />
				Now
			</span>
			<span className="now-card__clock">{clock}</span>
			{onBall !== null && (
				<span className="now-card__side">
					<SideMark side={onBall.side} />
					{codeOf(teams, onBall.side)} on the ball
				</span>
			)}
			{asked && (
				<span className="now-card__asked">
					Asked in the panel
					<ArrowIcon />
				</span>
			)}
		</div>
		<p className="now-card__line">
			{onBall === null ? (
				'Play goes on.'
			) : (
				<>
					<span className="now-card__number">#{onBall.touch.number}</span> {onBall.touch.surname}{' '}
					{onBall.touch.action}, {onBall.touch.where}.
				</>
			)}
		</p>
		{!compact && onBall !== null && (
			<div className="now-card__thirds">
				<div className="now-card__strip" role="img" aria-label={`Ball ${onBall.touch.where}`}>
					{THIRDS.map(third => {
						const here = third.zones.includes(onBall.touch.zone)
						return (
							<span
								key={third.label}
								className={here ? 'now-card__third now-card__third--here' : 'now-card__third'}>
								{here && <BallIcon />}
								{here && onBall.touch.zone === 'box' ? 'In the box' : third.label}
							</span>
						)
					})}
				</div>
				<span className="now-card__caption">
					Thirds as seen by the team on the ball, attacking left to right.
				</span>
			</div>
		)}
	</section>
)

const NowIcon = () => (
	<svg className="now-card__icon" viewBox="0 0 24 24" aria-hidden="true">
		<circle cx="12" cy="12" r="3.5" fill="currentColor" />
		<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="2" />
	</svg>
)

const ArrowIcon = () => (
	<svg className="now-card__icon" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
	</svg>
)

const BallIcon = () => (
	<svg className="now-card__ball" viewBox="0 0 24 24" aria-hidden="true">
		<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2.5" />
		<circle cx="12" cy="12" r="3.5" fill="currentColor" />
	</svg>
)

export default NowCard
