import { useEffect, useId, useRef } from 'react'
import type { Status } from '../../api/client.ts'
import Crest from '../Shared/Crest.tsx'
import { DEMO_OPTIONS, FEED_SPEEDS, PACES, THEMES, type Pace, type Playback, type Theme } from './index.support.ts'
import './index.css'

export interface PreferencesProps {
	/** The viewer's record; null while it loads. */
	status: Status | null
	theme: Theme
	playback: Playback
	/** True while a change of pace is being saved. */
	busy: boolean
	onPace: (pace: Pace) => void
	onTheme: (theme: Theme) => void
	onPlayback: (playback: Playback) => void
	/** Go to the club picker; only offered while the team can still change. */
	onChangeTeam: () => void
	/** Close and go back to the screen underneath, as it was. */
	onBack: () => void
}

/** Preferences (S8), over any screen: how often questions come, your team, the theme, and how the match feed
 * plays. */
const Preferences = ({
	status,
	theme,
	playback,
	busy,
	onPace,
	onTheme,
	onPlayback,
	onChangeTeam,
	onBack
}: PreferencesProps) => {
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const questionsId = useId()
	const themeId = useId()
	const speedId = useId()
	const demoId = useId()

	useEffect(() => {
		heading.current?.focus()
	}, [])

	useEffect(() => {
		const close = (event: KeyboardEvent) => {
			if (event.key === 'Escape') onBack()
		}
		document.addEventListener('keydown', close)
		return () => {
			document.removeEventListener('keydown', close)
		}
	}, [onBack])

	const shown = status?.pace_next ?? status?.pace ?? 'normal'
	return (
		<section className="preferences" aria-labelledby={headingId}>
			<button
				type="button"
				className="text-button preferences__back"
				aria-label="Close preferences and go back to where you were"
				onClick={onBack}>
				← Back
			</button>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="preferences__heading screen-heading">
				Preferences
			</h2>
			{status === null && <p role="status">Finding your preferences…</p>}
			{status !== null && (
				<>
					<fieldset className="preferences__group" aria-describedby={questionsId} disabled={busy}>
						<legend className="preferences__legend">Questions</legend>
						<div className="segments">
							{PACES.map(pace => (
								<label key={pace.value} className="segments__option">
									<input
										type="radio"
										name="pace"
										value={pace.value}
										checked={shown === pace.value}
										onChange={() => {
											onPace(pace.value)
										}}
									/>
									<span>{pace.label}</span>
								</label>
							))}
						</div>
						<p id={questionsId} className="preferences__help">
							Normal: 2–4 during play, in settled possession or while the ball is dead, and up to 2 at
							each break. Rarely: 1 during play. Off: no questions, and the reports still come.
						</p>
						{status.pace_next !== null && (
							<p className="preferences__pending" role="status">
								From your next match: this one carries on as it started.
							</p>
						)}
					</fieldset>

					<section className="preferences__group" aria-label="Your team">
						<h3 className="preferences__legend">Your team</h3>
						{status.club === null ? (
							<p className="preferences__help">No team picked.</p>
						) : (
							<p className="preferences__team">
								<Crest code={status.club.code} size={36} />
								<span className="preferences__code">{status.club.code}</span>
								<span className="preferences__club">{status.club.name}</span>
								{status.can_choose_club && (
									<button type="button" className="text-button" onClick={onChangeTeam}>
										Change
									</button>
								)}
							</p>
						)}
						<p className="preferences__help">
							{status.can_choose_club
								? 'Your team is listed first before every match and always attacks up the screen.'
								: 'Your team is settled once you’ve started watching.'}
						</p>
					</section>

					<fieldset className="preferences__group" aria-describedby={themeId}>
						<legend className="preferences__legend">Theme</legend>
						<div className="segments">
							{THEMES.map(option => (
								<label key={option.value} className="segments__option">
									<input
										type="radio"
										name="theme"
										value={option.value}
										checked={theme === option.value}
										onChange={() => {
											onTheme(option.value)
										}}
									/>
									<span>{option.label}</span>
								</label>
							))}
						</div>
						<p id={themeId} className="preferences__help">
							Kept in this browser. Match device follows your phone or computer.
						</p>
					</fieldset>

					<fieldset className="preferences__group" aria-describedby={speedId}>
						<legend className="preferences__legend">Feed speed</legend>
						<div className="segments">
							{FEED_SPEEDS.map(option => (
								<label key={option.value} className="segments__option">
									<input
										type="radio"
										name="feed-speed"
										value={option.value}
										checked={playback.speed === option.value}
										onChange={() => {
											onPlayback({ ...playback, speed: option.value })
										}}
									/>
									<span>{option.label}</span>
								</label>
							))}
						</div>
						<p id={speedId} className="preferences__help">
							How fast the match feed plays between questions. 1× is real time. Kept in this browser.
						</p>
					</fieldset>

					<fieldset className="preferences__group" aria-describedby={demoId}>
						<legend className="preferences__legend">Demo mode</legend>
						<div className="segments">
							{DEMO_OPTIONS.map(option => (
								<label key={option.label} className="segments__option">
									<input
										type="radio"
										name="demo"
										value={option.label}
										checked={playback.demo === option.value}
										onChange={() => {
											onPlayback({ ...playback, demo: option.value })
										}}
									/>
									<span>{option.label}</span>
								</label>
							))}
						</div>
						<p id={demoId} className="preferences__help">
							On, no wait between questions is longer than 20 seconds: a long one plays faster to fit.
						</p>
					</fieldset>
				</>
			)}
		</section>
	)
}

export default Preferences
