import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import type { Club } from '../../api/client.ts'
import { stepFrom } from '../Shared/AnswerGroup/index.support.ts'
import Crest from '../Shared/Crest.tsx'
import './index.css'
import { pickForMe } from './index.support.ts'

export interface PickTeamProps {
	clubs: readonly Club[]
	/** The viewer's club, if they have one and are changing it. */
	chosen: number | null
	/** Where "Pick one for me" starts, chosen by the server from the viewer's name. */
	suggested: number
	busy: boolean
	onChoose: (club: number) => void
}

/** Pick the team to support: the clubs as one radio group, with "Pick one for me" for a viewer with no favourite. */
const PickTeam = ({ clubs, chosen, suggested, busy, onChoose }: PickTeamProps) => {
	const [selected, setSelected] = useState(chosen)
	const [announced, setAnnounced] = useState('')
	const heading = useRef<HTMLHeadingElement>(null)
	const rows = useRef<(HTMLButtonElement | null)[]>([])
	const headingId = useId()
	const current = Math.max(
		0,
		clubs.findIndex(club => club.team_id === selected)
	)
	const picked = clubs.find(club => club.team_id === selected)

	useEffect(() => {
		heading.current?.focus()
	}, [])

	const onKeyDown = (event: KeyboardEvent) => {
		const next = stepFrom(current, event.key, clubs.length)
		const club = next === undefined ? undefined : clubs[next]
		if (next === undefined || club === undefined) {
			return
		}
		event.preventDefault()
		rows.current[next]?.focus()
		setSelected(club.team_id)
	}

	const pickOne = () => {
		const club = clubs.find(each => each.team_id === pickForMe(clubs, suggested, selected))
		if (club !== undefined) {
			setSelected(club.team_id)
			setAnnounced(`Picked ${club.name}`)
		}
	}

	const confirm = () => {
		if (picked !== undefined && !busy) {
			onChoose(picked.team_id)
		}
	}

	return (
		<section className="pick-team" aria-labelledby={headingId}>
			<h2 id={headingId} ref={heading} tabIndex={-1} className="pick-team__heading screen-heading">
				Pick your team
			</h2>
			<p className="pick-team__intro">
				Your three matches are theirs, and they're shown first before every match. You can change this until
				your first question.
			</p>
			<div role="radiogroup" aria-labelledby={headingId} className="pick-team__clubs" onKeyDown={onKeyDown}>
				{clubs.map((club, index) => {
					const checked = club.team_id === selected
					return (
						<button
							key={club.team_id}
							ref={element => {
								rows.current[index] = element
							}}
							type="button"
							role="radio"
							aria-checked={checked}
							tabIndex={index === current ? 0 : -1}
							className="pick-team__club"
							onClick={() => {
								setSelected(club.team_id)
							}}>
							<Crest code={club.code} size={36} />
							<span className="pick-team__name">{club.name}</span>
							<span className="pick-team__code">{club.code}</span>
							<span className="pick-team__radio" aria-hidden="true" />
						</button>
					)
				})}
			</div>
			<p className="visually-hidden" aria-live="polite">
				{announced}
			</p>
			<div className="pick-team__actions">
				<button type="button" className="pick-team__for-me" onClick={pickOne}>
					Pick one for me
				</button>
				<button
					type="button"
					className="primary-button"
					aria-disabled={picked === undefined || busy}
					onClick={confirm}>
					{picked === undefined ? 'Pick a team to continue' : `Continue with ${picked.name}`}
				</button>
			</div>
		</section>
	)
}

export default PickTeam
