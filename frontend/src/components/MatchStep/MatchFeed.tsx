import type { Heard, Teams } from './Commentary.support.ts'
import FeedList from './FeedList.tsx'
import MatchStats from './MatchStats.tsx'
import MovingPitch from './MovingPitch.tsx'
import type { Track } from './MovingPitch.support.ts'
import NowCard from './NowCard.tsx'
import Scorebug from './Scorebug.tsx'
import './MatchFeed.css'

export interface MatchFeedProps {
	teams: Teams
	heard: Heard
	clock: string
	countdown: string
	/** Whether the question is waiting in the panel. */
	asked: boolean
	/** How many times faster than real time the clock runs; null when it doesn't run. */
	speed: number | null
	/** Where the players and the ball were, from the server. */
	track: Track
	/** Seconds on the match clock. */
	at: number
}

/** The match standing in for the viewer's TV on a wide screen: the moving pitch, the scorebug, the latest action, the
 * numbers and the feed from kick-off, all following the match clock. */
const MatchFeed = ({ teams, heard, clock, countdown, asked, speed, track, at }: MatchFeedProps) => (
	<div className="match-feed">
		<div className="match-feed__top">
			<span className="match-feed__stand-in">
				<TvIcon />
				Stand-in for your TV
			</span>
			<span className="match-feed__note">
				Pitch and feed · follow the match clock
				{speed !== null && (
					<span className="match-feed__speed" aria-label={`Playing at ${String(speed)} times real speed`}>
						<SpeedIcon />
						{speed}×
					</span>
				)}
			</span>
		</div>
		<div className="match-feed__pitch">
			<MovingPitch track={track} at={at} yours={teams.yours} />
		</div>
		<Scorebug teams={teams} stats={heard.stats} clock={clock} countdown={countdown} />
		<NowCard teams={teams} clock={clock} onBall={heard.onBall} asked={asked} />
		{heard.stats !== null && <MatchStats stats={heard.stats} teams={teams} />}
		<FeedList entries={heard.feed} teams={teams} />
	</div>
)

const SpeedIcon = () => (
	<svg className="match-feed__speed-icon" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M4 6l8 6-8 6zM12 6l8 6-8 6z" />
	</svg>
)

const TvIcon = () => (
	<svg className="match-feed__tv" viewBox="0 0 24 24" aria-hidden="true">
		<rect x="3" y="4" width="18" height="12" rx="2" />
		<path d="M8 20h8M12 16v4" />
	</svg>
)

export default MatchFeed
