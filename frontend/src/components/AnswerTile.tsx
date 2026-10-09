import type { Ref } from 'react'
import type { TileState } from './AnswerGroup.support.ts'
import './AnswerTile.css'

export interface AnswerTileProps {
	optionKey: string
	label: string
	state: TileState
	/** Whether this is the viewer's pick, before or after the reveal. */
	checked: boolean
	layout: 'columns' | 'rows'
	focusable: boolean
	disabled: boolean
	onSelect: () => void
	buttonRef?: Ref<HTMLButtonElement>
}

/** One answer: a radio button showing its letter and label, and after the reveal an icon and a word for its state. */
const AnswerTile = ({
	optionKey,
	label,
	state,
	checked,
	layout,
	focusable,
	disabled,
	onSelect,
	buttonRef
}: AnswerTileProps) => (
	<button
		ref={buttonRef}
		type="button"
		role="radio"
		aria-checked={checked}
		aria-disabled={disabled}
		tabIndex={focusable ? 0 : -1}
		className={`answer-tile answer-tile--${state} answer-tile--${layout}`}
		onClick={() => {
			if (!disabled) {
				onSelect()
			}
		}}>
		<span className="answer-tile__key">
			{optionKey}
			{state === 'correct' && <CheckIcon />}
			{state === 'incorrect' && <CrossIcon />}
		</span>
		{state === 'correct' && <span className="answer-tile__word">Answer</span>}
		{state === 'incorrect' && <span className="answer-tile__word">Your pick</span>}
		<span className="answer-tile__label">{label}</span>
		{state === 'selected' && <RadioDot />}
	</button>
)

const CheckIcon = () => (
	<svg className="answer-tile__icon" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M5 12.5l4.5 4.5L19 7" />
	</svg>
)

const CrossIcon = () => (
	<svg className="answer-tile__icon" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M6 6l12 12M18 6L6 18" />
	</svg>
)

const RadioDot = () => (
	<svg className="answer-tile__dot" viewBox="0 0 24 24" aria-hidden="true">
		<circle cx="12" cy="12" r="9" />
		<circle className="answer-tile__dot-fill" cx="12" cy="12" r="3.5" />
	</svg>
)

export default AnswerTile
