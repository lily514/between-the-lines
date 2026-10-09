import { useRef, type KeyboardEvent } from 'react'
import './AnswerGroup.css'
import { layoutFor, stepFrom, tileState, type Choice, type Outcome } from './AnswerGroup.support.ts'
import AnswerTile from './AnswerTile.tsx'

export interface AnswerGroupProps {
	/** What the group is for, read by screen readers ("Your answer"). */
	label: string
	choices: readonly Choice[]
	selected: string | null
	onSelect: (key: string) => void
	disabled?: boolean
	/** After the reveal: the right option and the viewer's pick. The tiles then show the result and can't change. */
	outcome?: Outcome
}

/** The answer options as a radio group: one tab stop, arrow keys move and select, as native radios do. */
const AnswerGroup = ({ label, choices, selected, onSelect, disabled = false, outcome }: AnswerGroupProps) => {
	const buttons = useRef<(HTMLButtonElement | null)[]>([])
	const locked = disabled || outcome !== undefined
	const checkedKey = outcome === undefined ? selected : outcome.chosen
	const current = Math.max(
		0,
		choices.findIndex(c => c.key === checkedKey)
	)
	const layout = layoutFor(choices)

	const onKeyDown = (event: KeyboardEvent) => {
		const next = stepFrom(current, event.key, choices.length)
		const choice = next === undefined ? undefined : choices[next]
		if (next === undefined || choice === undefined) {
			return
		}
		event.preventDefault()
		buttons.current[next]?.focus()
		if (!locked) {
			onSelect(choice.key)
		}
	}

	return (
		<div
			role="radiogroup"
			aria-label={label}
			aria-disabled={locked}
			className={`answer-group answer-group--${layout}`}
			onKeyDown={onKeyDown}>
			{choices.map((choice, index) => (
				<AnswerTile
					key={choice.key}
					buttonRef={element => {
						buttons.current[index] = element
					}}
					optionKey={choice.key}
					label={choice.label}
					state={tileState(choice.key, selected, outcome)}
					checked={choice.key === checkedKey}
					layout={layout}
					focusable={index === current}
					disabled={locked}
					onSelect={() => {
						onSelect(choice.key)
					}}
				/>
			))}
		</div>
	)
}

export default AnswerGroup
