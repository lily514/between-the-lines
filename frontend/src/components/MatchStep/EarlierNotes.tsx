import { useEffect, useId, useRef } from 'react'
import type { Heard, Teams } from './Commentary.support.ts'
import FeedList from './FeedList.tsx'
import MatchStats from './MatchStats.tsx'
import './EarlierNotes.css'

export interface EarlierNotesProps {
	teams: Teams
	heard: Heard
	clock: string
	onClose: () => void
}

/** The phone's sheet of earlier notes: the match's numbers and the whole feed so far, closed by its button, Esc, or a
 * tap outside it. */
const EarlierNotes = ({ teams, heard, clock, onClose }: EarlierNotesProps) => {
	const dialog = useRef<HTMLDialogElement>(null)
	const headingId = useId()

	useEffect(() => {
		dialog.current?.showModal()
	}, [])

	const close = () => {
		dialog.current?.close()
	}
	return (
		<dialog
			ref={dialog}
			className="earlier-notes"
			aria-labelledby={headingId}
			onClose={onClose}
			onClick={event => {
				if (event.target === event.currentTarget) close()
			}}>
			<div className="earlier-notes__head">
				<div className="earlier-notes__title">
					<h2 id={headingId} className="earlier-notes__heading">
						Earlier notes
					</h2>
					<span className="earlier-notes__fixture">
						{teams.home} v {teams.away} · <span className="earlier-notes__clock">{clock}</span>
					</span>
				</div>
				<button type="button" className="text-button" onClick={close}>
					Close
				</button>
			</div>
			{heard.stats !== null && <MatchStats stats={heard.stats} teams={teams} />}
			<FeedList entries={heard.feed} teams={teams} level={3} />
		</dialog>
	)
}

export default EarlierNotes
