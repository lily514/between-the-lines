import './ExampleCard.css'

export interface ExampleCardProps {
	/** "You might get", or "At Solid, you might get". */
	label: string
	prompt: string
}

/** The example card on a story step: a question the viewer might really get, worded as the Tutor would. */
const ExampleCard = ({ label, prompt }: ExampleCardProps) => (
	<div className="example-card">
		<svg className="example-card__icon" viewBox="0 0 20 20" aria-hidden="true">
			<path d="M3 4.5 h14 v9 h-8 l-4 3 v-3 h-2 z" />
		</svg>
		<div>
			<p className="example-card__label">{label}</p>
			<p className="example-card__prompt">{prompt}</p>
		</div>
	</div>
)

export default ExampleCard
