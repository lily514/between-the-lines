// @vitest-environment node
import { readFileSync } from 'node:fs'
import openapiTS, { astToString } from 'openapi-typescript'

const read = (name: string) => readFileSync(`src/api/${name}`, 'utf8')

// schema.d.ts must be what `npm run api-types` makes from the committed openapi.json.
test('the API types match the committed schema', async () => {
	const generated = astToString(await openapiTS(read('openapi.json')))
	expect(strip(read('schema.d.ts')), 'schema.d.ts is out of date: run `npm run api-types`').toBe(strip(generated))
})

// The CLI adds a banner the library leaves out.
const strip = (text: string) => text.replace(/^\/\*\*[\s\S]*?\*\/\s*/, '').trim()
