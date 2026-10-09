import { render, screen } from '@testing-library/react'
import App from './App.tsx'

test('the page renders its title', () => {
	render(<App />)
	expect(screen.getByRole('heading', { name: 'Between the Lines' })).toBeInTheDocument()
})
