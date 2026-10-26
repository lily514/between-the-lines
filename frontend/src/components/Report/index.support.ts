import type { Report } from '../../api/client.ts'

type Concept = Report['concepts'][number]

/** The result from the viewer's side at full time, their team's goals first: "Your team, Ripon Wardens, won 2–1." */
export const resultLine = (report: Report): string | null => {
	if (report.your_team === null || report.your_result === null) {
		return null
	}
	const home = report.your_team === 'home'
	const name = home ? report.home : report.away
	const [ours, theirs] = home ? [report.home_goals, report.away_goals] : [report.away_goals, report.home_goals]
	return `Your team, ${name}, ${report.your_result} ${String(ours)}–${String(theirs)}.`
}

/** Each strand with its concepts asked about now, in the report's strand order; a strand may have none. */
export const byStrand = (report: Report): { key: string; name: string; concepts: Concept[] }[] =>
	report.strands.map(strand => ({
		key: strand.key,
		name: strand.name,
		concepts: report.concepts.filter(concept => concept.strand === strand.key)
	}))
