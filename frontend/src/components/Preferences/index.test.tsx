import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { startStatus } from '../../test-fixtures/summaries.ts'
import Preferences from './index.tsx'
import { applyTheme, rememberedTheme, rememberTheme } from './index.support.ts'

const show = (props: Partial<Parameters<typeof Preferences>[0]> = {}) => {
	const handlers = { onPace: vi.fn(), onTheme: vi.fn(), onChangeTeam: vi.fn(), onBack: vi.fn() }
	render(<Preferences status={startStatus} theme="system" busy={false} {...handlers} {...props} />)
	return handlers
}

beforeEach(() => {
	localStorage.clear()
	delete document.documentElement.dataset.theme
})

test('questions are a radio group, with the viewer’s pace chosen', async () => {
	const { onPace } = show()
	expect(screen.getByRole('heading', { name: 'Preferences' })).toHaveFocus()
	expect(screen.getByRole('radio', { name: 'Normal' })).toBeChecked()
	await userEvent.click(screen.getByRole('radio', { name: 'Off' }))
	expect(onPace).toHaveBeenCalledWith('off')
})

test('a pace waiting for the next match shows as chosen, and says when it starts', () => {
	show({ status: { ...startStatus, pace_next: 'rarely' } })
	expect(screen.getByRole('radio', { name: 'Rarely' })).toBeChecked()
	expect(screen.getByText(/From your next match/)).toBeInTheDocument()
})

test('your team can be changed only while it can still change', async () => {
	const { onChangeTeam } = show()
	await userEvent.click(screen.getByRole('button', { name: 'Change' }))
	expect(onChangeTeam).toHaveBeenCalledOnce()
})

test('a settled team has no Change', () => {
	show({ status: { ...startStatus, can_choose_club: false } })
	expect(screen.queryByRole('button', { name: 'Change' })).toBeNull()
	expect(screen.getByText(/settled once you’ve started watching/)).toBeInTheDocument()
})

test('the theme is chosen here, and kept in this browser', async () => {
	const { onTheme } = show()
	await userEvent.click(screen.getByRole('radio', { name: 'Light' }))
	expect(onTheme).toHaveBeenCalledWith('light')
	rememberTheme('light')
	expect(rememberedTheme()).toBe('light')
	applyTheme('light')
	expect(document.documentElement.dataset.theme).toBe('light')
	rememberTheme('system')
	applyTheme('system')
	expect(rememberedTheme()).toBe('system')
	expect(document.documentElement.dataset.theme).toBeUndefined()
})

test('Back and Esc close Preferences', async () => {
	const { onBack } = show()
	await userEvent.click(screen.getByRole('button', { name: 'Close preferences and go back to where you were' }))
	await userEvent.keyboard('{Escape}')
	expect(onBack).toHaveBeenCalledTimes(2)
})
