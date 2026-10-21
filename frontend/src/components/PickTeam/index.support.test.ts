import { clubs } from '../../test-fixtures/summaries.ts'
import { pickForMe } from './index.support.ts'

test('the first pick is the suggestion, and each one after moves on to the next club', () => {
	expect(pickForMe(clubs, 2, null)).toBe(2)
	expect(pickForMe(clubs, 2, 2)).toBe(3)
	expect(pickForMe(clubs, 2, 3)).toBe(1)
})

test('a club already picked by hand is never picked again', () => {
	expect(pickForMe(clubs, 2, 1)).toBe(2)
})

test('an unknown suggestion falls back to the first club, and no clubs gives nothing', () => {
	expect(pickForMe(clubs, 99, null)).toBe(1)
	expect(pickForMe([], 2, null)).toBeNull()
})
