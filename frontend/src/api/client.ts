import type { components } from './schema'

type Schemas = components['schemas']
export type Status = Schemas['StatusOut']
export type Question = Schemas['QuestionOut']
export type FullTime = Schemas['FullTimeOut']
export type Feedback = Schemas['FeedbackOut']
export type NextStep = Question | FullTime
export type Picture = Schemas['PictureOut']
export type Marker = Schemas['MarkerOut']
export type Club = Schemas['ClubOut']
export type TeamSheet = Schemas['TeamSheetOut']
export type SheetTeam = Schemas['SheetTeamOut']
export type SheetPlayer = Schemas['SheetPlayerOut']
export type MatchSummary = Schemas['MatchOut']
export type ConceptMap = Schemas['ConceptMapOut']
export type MapConcept = Schemas['MapConceptOut']
export type Report = Schemas['ReportOut']
export type ReportAt = Report['at']

/** A response other than 2xx. `status` lets callers tell a stale question (409) from a bad name (422). */
export class ApiError extends Error {
	readonly status: number

	constructor(status: number, message: string) {
		super(message)
		this.name = 'ApiError'
		this.status = status
	}
}

const viewerPath = (viewerId: string) => `/api/viewers/${encodeURIComponent(viewerId)}`

export const startViewer = (viewerId: string, seed?: number) => {
	const body: Schemas['StartIn'] = seed === undefined ? { viewer_id: viewerId } : { viewer_id: viewerId, seed }
	return request<Status>('/api/viewers', body)
}

export const getStatus = (viewerId: string) => request<Status>(viewerPath(viewerId))

export const getClubs = () => request<Club[]>('/api/clubs')

export const getTeamSheet = (viewerId: string) => request<TeamSheet>(`${viewerPath(viewerId)}/team-sheet`)

export const chooseClub = (viewerId: string, club: number) => {
	const body: Schemas['ClubIn'] = { club }
	return request<Status>(`${viewerPath(viewerId)}/club`, body, 'PUT')
}

export const getMatches = (viewerId: string) => request<MatchSummary[]>(`${viewerPath(viewerId)}/matches`)

/** The whole curriculum: with a viewer, their level on each concept asked about now; without one, the map alone. */
export const getConceptMap = (viewerId: string | null) =>
	request<ConceptMap>(viewerId === null ? '/api/concept-map' : `${viewerPath(viewerId)}/concept-map`)

export const getReport = (viewerId: string, matchNumber: number, at: ReportAt) =>
	request<Report>(`${viewerPath(viewerId)}/matches/${String(matchNumber)}/report?at=${at}`)

export const nextStep = (viewerId: string) => request<NextStep>(`${viewerPath(viewerId)}/next`, {})

export const answer = (viewerId: string, packId: string, key: string) => {
	const body: Schemas['AnswerIn'] = { pack_id: packId, key }
	return request<Feedback>(`${viewerPath(viewerId)}/answers`, body)
}

const request = async <T>(path: string, body?: object, method = 'POST'): Promise<T> => {
	const init: RequestInit =
		body === undefined
			? { headers: { Accept: 'application/json' } }
			: {
					method,
					headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
					body: JSON.stringify(body)
				}
	const response = await fetch(path, init)
	if (!response.ok) {
		throw new ApiError(response.status, await errorMessage(response))
	}
	return (await response.json()) as T
}

// FastAPI sends `{detail: "..."}` for its own errors and `{detail: [{msg}, ...]}` for invalid input.
const errorMessage = async (response: Response): Promise<string> => {
	try {
		const data = (await response.json()) as { detail?: unknown }
		if (typeof data.detail === 'string') {
			return data.detail
		}
		if (Array.isArray(data.detail)) {
			return data.detail.map(item => String((item as { msg?: unknown }).msg ?? item)).join('; ')
		}
	} catch {
		// Not JSON: fall back to the status text.
	}
	return response.statusText || `request failed with status ${String(response.status)}`
}
