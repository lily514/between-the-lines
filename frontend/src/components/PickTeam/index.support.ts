import type { Club } from '../../api/client.ts'

/** "Pick one for me": the server's suggestion first, then on through the list, never the club already picked. */
export const pickForMe = (clubs: readonly Club[], suggested: number, current: number | null): number | null => {
	if (clubs.length === 0) {
		return null
	}
	const start = current ?? suggested
	const index = clubs.findIndex(club => club.team_id === start)
	if (current === null && index >= 0) {
		return suggested
	}
	return clubs[(index + 1) % clubs.length]?.team_id ?? null
}
