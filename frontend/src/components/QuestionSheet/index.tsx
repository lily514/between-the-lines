import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import type { Question } from '../../api/client.ts'
import AnswerGroup from '../Shared/AnswerGroup/index.tsx'
import LockIn from './LockIn.tsx'
import PhasePill from '../Shared/PhasePill.tsx'
import Pitch from '../Shared/Pitch/index.tsx'
import { pitchOptions } from '../Shared/Pitch/index.support.ts'
import './index.css'
import { clockLine, earlierAt, isLive, keyedOption, pitchLabel, shownPath, sheetPill } from './index.support.ts'

export interface QuestionSheetProps {
	question: Question
	onLockIn: (key: string) => void
	/** True while the answer is being sent: the pick can't change. */
	busy?: boolean
}

/** A question as the viewer meets it: where play is, the question, the pitch, the options and Lock in.
 *
 * Give it `key={question.pack_id}` so a new question starts with no pick. Keys 1–3 pick and Enter locks in, only while
 * focus is inside the sheet. */
const QuestionSheet = ({ question, onLockIn, busy = false }: QuestionSheetProps) => {
	const [selected, setSelected] = useState<string | null>(null)
	const heading = useRef<HTMLHeadingElement>(null)
	const headingId = useId()
	const pill = sheetPill(question)
	const earlier = earlierAt(question)

	useEffect(() => {
		heading.current?.focus()
	}, [])

	const onKeyDown = (event: KeyboardEvent) => {
		if (busy || event.altKey || event.ctrlKey || event.metaKey) {
			return
		}
		const keyed = keyedOption(question, event.key)
		if (keyed !== undefined) {
			event.preventDefault()
			setSelected(keyed)
		} else if (event.key === 'Enter' && selected !== null) {
			event.preventDefault()
			onLockIn(selected)
		}
	}

	return (
		<section className="question-sheet" aria-labelledby={headingId} onKeyDown={onKeyDown}>
			<header className="question-sheet__bar">
				<PhasePill phase={pill.phase} detail={pill.detail} />
				<span className="question-sheet__clock">{clockLine(question)}</span>
			</header>
			{earlier !== undefined && (
				<p className="question-sheet__earlier">
					<RewindIcon />
					Earlier, at <span className="question-sheet__time">{earlier}</span>
				</p>
			)}
			<h2 id={headingId} ref={heading} tabIndex={-1} className="question-sheet__question">
				{question.text}
			</h2>
			<p className="question-sheet__note">
				{isLive(question)
					? 'Freeze-frame. The match carries on, on your TV.'
					: 'This already happened. What did you see?'}
			</p>
			<div className="question-sheet__pitch">
				<Pitch
					picture={question.picture}
					options={pitchOptions(question)}
					path={shownPath(question)}
					crop="moment"
					label={pitchLabel(question)}
					yours={question.your_team}
				/>
			</div>
			<AnswerGroup
				label="Your answer"
				choices={question.options}
				selected={selected}
				onSelect={setSelected}
				disabled={busy}
			/>
			<div className="question-sheet__actions">
				<LockIn selected={selected} busy={busy} onLockIn={onLockIn} />
			</div>
		</section>
	)
}

const RewindIcon = () => (
	<svg className="question-sheet__icon" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M4 12a8 8 0 1 0 2.4-5.7" />
		<path d="M4 4v4h4" />
	</svg>
)

export default QuestionSheet
