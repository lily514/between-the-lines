import type { FullTime } from '../../api/client.ts'

/** The result from the viewer's side, their team's goals first: "Your team, Ripon Wardens, won 2–1." */
export const resultLine = (summary: FullTime): string | null => {
	if (summary.your_team === null || summary.your_result === null) {
		return null
	}
	const home = summary.your_team === 'home'
	const name = home ? summary.home : summary.away
	const [ours, theirs] = home ? [summary.home_goals, summary.away_goals] : [summary.away_goals, summary.home_goals]
	return `Your team, ${name}, ${summary.your_result} ${String(ours)}–${String(theirs)}.`
}
