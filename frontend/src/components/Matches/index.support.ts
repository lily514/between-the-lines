import type { MatchSummary } from '../../api/client.ts'

/** The match the screen leads with: the one part-way through, or else the next to watch; null when all are done. */
export const featured = (matches: MatchSummary[]): MatchSummary | null =>
	matches.find(match => match.state === 'in_progress') ?? matches.find(match => match.state === 'upcoming') ?? null

/** A score as the API gives it, home first: "1–0". */
export const scoreLine = (score: { home: number; away: number }) => `${String(score.home)}–${String(score.away)}`
