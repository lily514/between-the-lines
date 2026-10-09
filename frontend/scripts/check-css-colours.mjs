// Component CSS takes its colours from the tokens in src/styles/tokens.css, never as literals.
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'

const ROOT = 'src'
const TOKENS = join('src', 'styles', 'tokens.css')
const LITERAL = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(/g

const cssFiles = dir =>
	readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
		const path = join(dir, entry.name)
		if (entry.isDirectory()) return cssFiles(path)
		return entry.name.endsWith('.css') ? [path] : []
	})

const problems = cssFiles(ROOT)
	.filter(path => relative('.', path) !== TOKENS)
	.flatMap(path =>
		readFileSync(path, 'utf8')
			.split('\n')
			.flatMap((line, index) =>
				[...line.matchAll(LITERAL)].map(match => `${path}:${String(index + 1)}: ${match[0]}`)
			)
	)

if (problems.length > 0) {
	console.error('Colour literals outside tokens.css (use a var(--token) instead):')
	for (const problem of problems) console.error(`  ${problem}`)
	process.exit(1)
}
