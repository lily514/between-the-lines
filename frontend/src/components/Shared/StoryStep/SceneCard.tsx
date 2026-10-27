import type { Band } from '../../../api/client.ts'
import { FIXTURES } from '../../../scenes/fixtures/index.ts'
import { SPECS } from '../../../scenes/index.ts'
import LevelIcon from '../LevelIcon.tsx'
import Scene from '../Scene/index.tsx'
import './SceneCard.css'

export interface SceneCardProps {
	/** The concept whose scene to draw; without a spec or fixture, a dashed card says the scene is coming. */
	concept: string
	band: Band
	/** The tag at the top left: "Now Solid" with its icon, or "First look" with none. */
	tag?: { text: string; band: Band | null }
}

/** A concept's scene at a level, with its tag, in the story step's card. */
const SceneCard = ({ concept, band, tag }: SceneCardProps) => {
	const spec = SPECS[concept]
	const fixture = FIXTURES[concept]
	return (
		<div className="scene-card">
			{spec !== undefined && fixture !== undefined ? (
				<Scene spec={spec} fixture={fixture} band={band} name={fixture.name} />
			) : (
				<div className="scene-card__later" data-testid="scene-later">
					<span>Scene coming</span>
				</div>
			)}
			{tag !== undefined && (
				<span className="scene-card__tag">
					{tag.band !== null && <LevelIcon band={tag.band} />}
					{tag.text}
				</span>
			)}
		</div>
	)
}

export default SceneCard
