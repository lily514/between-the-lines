import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// `btl serve` (run from backend/) listens here.
const API = 'http://127.0.0.1:8000'

export default defineConfig({
	plugins: [react()],
	server: {
		proxy: { '/api': API }
	},
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: ['./src/test-setup.ts'],
		restoreMocks: true
	}
})
