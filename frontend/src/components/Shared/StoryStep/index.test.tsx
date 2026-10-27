import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExampleCard from './ExampleCard.tsx'
import SceneCard from './SceneCard.tsx'
import StoryStep from './index.tsx'

test('a step shows its place in the flow, Skip until the last step, and Back from the second', async () => {
	const on = { onSkip: vi.fn(), onBack: vi.fn(), next: vi.fn() }
	const { rerender } = render(
		<StoryStep
			flow="Before match 2"
			index={0}
			count={3}
			onSkip={on.onSkip}
			next={{ label: 'Next', onClick: on.next }}
			title="First">
			<p>Body</p>
		</StoryStep>
	)
	expect(screen.getByText('Before match 2')).toBeInTheDocument()
	expect(screen.getByText('1 of 3')).toBeInTheDocument()
	expect(screen.getByRole('heading', { level: 2, name: 'First' })).toHaveFocus()
	expect(screen.queryByRole('button', { name: 'Back' })).toBeNull()
	await userEvent.click(screen.getByRole('button', { name: 'Skip' }))
	expect(on.onSkip).toHaveBeenCalledOnce()
	await userEvent.click(screen.getByRole('button', { name: 'Next' }))
	expect(on.next).toHaveBeenCalledOnce()

	rerender(
		<StoryStep
			flow="Before match 2"
			index={2}
			count={3}
			onSkip={on.onSkip}
			onBack={on.onBack}
			next={{ label: 'On to Who’s playing', onClick: on.next }}
			title="Last">
			<p>Body</p>
		</StoryStep>
	)
	expect(screen.getByText('3 of 3')).toBeInTheDocument()
	expect(screen.queryByRole('button', { name: 'Skip' })).toBeNull()
	expect(screen.getByRole('heading', { level: 2, name: 'Last' })).toHaveFocus()
	await userEvent.click(screen.getByRole('button', { name: 'Back' }))
	expect(on.onBack).toHaveBeenCalledOnce()
	expect(screen.getByRole('button', { name: 'On to Who’s playing' })).toBeInTheDocument()
})

test('the segments are decoration, one per step, filled up to the current one', () => {
	const { container } = render(
		<StoryStep index={1} count={4} next={{ label: 'Next', onClick: vi.fn() }} title="Second">
			<p>Body</p>
		</StoryStep>
	)
	const segments = container.querySelectorAll('.story-step__segment')
	expect(segments).toHaveLength(4)
	expect(container.querySelectorAll('.story-step__segment--done')).toHaveLength(2)
	expect(segments[0]?.closest('[aria-hidden="true"]')).not.toBeNull()
})

test('the scene card tags the level with its icon, or First look with none, and says when a scene is coming', () => {
	const { container, rerender } = render(
		<SceneCard concept="offside" band="solid" tag={{ text: 'Now Solid', band: 'solid' }} />
	)
	expect(screen.getByText('Now Solid').querySelector('.level-icon')).not.toBeNull()
	expect(container.querySelector('.scene__svg')).toHaveAttribute('data-band', 'solid')
	rerender(<SceneCard concept="phase_of_play" band="getting_there" tag={{ text: 'First look', band: null }} />)
	expect(screen.getByText('First look').querySelector('.level-icon')).toBeNull()
	expect(screen.getByTestId('scene-later')).toBeInTheDocument()
})

test('the example card carries its label and the prompt', () => {
	render(<ExampleCard label="At Solid, you might get" prompt="How many lines did that pass break?" />)
	expect(screen.getByText('At Solid, you might get')).toBeInTheDocument()
	expect(screen.getByText('How many lines did that pass break?')).toBeInTheDocument()
})
