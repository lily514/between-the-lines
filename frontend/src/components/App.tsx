import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import {
	answer,
	ApiError,
	chooseClub,
	getClubs,
	getStatus,
	getTeamSheet,
	nextStep,
	startViewer,
	type Question,
	type Status
} from '../api/client.ts'
import './App.css'
import {
	forgetViewer,
	initialState,
	LOADING_CLUBS,
	LOADING_NEXT,
	LOADING_SHEET,
	LOADING_START,
	matchHeader,
	needsClub,
	reducer,
	rememberedViewer,
	rememberViewer,
	type Retry
} from './App.support.ts'
import ErrorPanel from './Shared/ErrorPanel.tsx'
import Feedback from './Feedback/index.tsx'
import FullTime from './FullTime/index.tsx'
import MatchStep from './MatchStep/index.tsx'
import PickTeam from './PickTeam/index.tsx'
import QuestionSheet from './QuestionSheet/index.tsx'
import TeamSheet from './TeamSheet/index.tsx'
import Welcome from './Welcome/index.tsx'

const messageOf = (error: unknown) =>
	error instanceof Error ? error.message : 'The server could not be reached. Check it is running, then try again.'

/** The learning loop in the browser: a name, then each match as a run of questions, feedback and a full-time summary.
 *
 * On a wide screen the companion sits in a side panel beside the viewer's own stream, and never covers it. */
const App = () => {
	const [remembered] = useState(rememberedViewer)
	const [state, dispatch] = useReducer(reducer, remembered, initialState)
	const viewer = state.viewer

	const fail = useCallback((error: unknown, retry: Retry) => {
		if (error instanceof ApiError && error.status === 404) {
			forgetViewer()
			dispatch({ type: 'forget', message: 'That record has gone. Start again with your name.' })
			return
		}
		dispatch({ type: 'failed', message: messageOf(error), retry })
	}, [])

	const loadNext = useCallback(
		async (id: string) => {
			dispatch({ type: 'loading', message: LOADING_NEXT })
			try {
				dispatch({ type: 'arrived', step: await nextStep(id) })
			} catch (error) {
				fail(error, { kind: 'next' })
			}
		},
		[fail]
	)

	const loadStatus = useCallback(
		async (id: string) => {
			dispatch({ type: 'loading', message: LOADING_START })
			try {
				dispatch({ type: 'started', status: await getStatus(id) })
			} catch (error) {
				fail(error, { kind: 'status' })
			}
		},
		[fail]
	)

	const loadSheet = useCallback(
		async (id: string, status: Status | null) => {
			dispatch({ type: 'loading', message: LOADING_SHEET })
			try {
				dispatch({ type: 'sheet', sheet: await getTeamSheet(id), status })
			} catch (error) {
				fail(error, { kind: 'sheet', status })
			}
		},
		[fail]
	)

	const loadPick = useCallback(
		async (status: Status) => {
			dispatch({ type: 'loading', message: LOADING_CLUBS })
			try {
				dispatch({ type: 'picking', status, clubs: await getClubs() })
			} catch (error) {
				fail(error, { kind: 'pick', status })
			}
		},
		[fail]
	)

	const choose = useCallback(
		async (id: string, club: number) => {
			dispatch({ type: 'choosing' })
			try {
				dispatch({ type: 'started', status: await chooseClub(id, club) })
			} catch (error) {
				// 409: the viewer has started watching (in another tab, say), so their team is settled.
				if (error instanceof ApiError && error.status === 409) {
					await loadStatus(id)
				} else {
					fail(error, { kind: 'choose', club })
				}
			}
		},
		[fail, loadStatus]
	)

	const start = useCallback(
		async (name: string, resume: boolean) => {
			dispatch({ type: 'loading', message: LOADING_START })
			try {
				const status = await startViewer(name)
				rememberViewer(status.viewer_id)
				if (needsClub(status)) {
					await loadPick(status)
				} else if (resume && !status.finished) {
					await loadNext(status.viewer_id)
				} else {
					dispatch({ type: 'started', status })
				}
			} catch (error) {
				if (error instanceof ApiError && error.status === 422) {
					forgetViewer()
					dispatch({ type: 'rejected', message: error.message, name })
				} else {
					fail(error, { kind: 'start', name })
				}
			}
		},
		[fail, loadNext, loadPick]
	)

	const send = useCallback(
		async (id: string, question: Question, key: string) => {
			dispatch({ type: 'sending' })
			try {
				dispatch({ type: 'answered', feedback: await answer(id, question.pack_id, key) })
			} catch (error) {
				// 409: this isn't the question the server is waiting on (another tab answered it), so fetch the one it is.
				if (error instanceof ApiError && error.status === 409) {
					await loadNext(id)
				} else {
					fail(error, { kind: 'answer', question, key })
				}
			}
		},
		[fail, loadNext]
	)

	// A remembered viewer carries on where they left off: the server replays their match to the waiting question.
	const resumed = useRef(false)
	useEffect(() => {
		if (remembered !== null && !resumed.current) {
			resumed.current = true
			void start(remembered, true)
		}
	}, [remembered, start])

	const retry = (what: Retry) => {
		if (what.kind === 'start') {
			void start(what.name, false)
		} else if (viewer !== null) {
			if (what.kind === 'next') void loadNext(viewer)
			else if (what.kind === 'status') void loadStatus(viewer)
			else if (what.kind === 'pick') void loadPick(what.status)
			else if (what.kind === 'choose') void choose(viewer, what.club)
			else if (what.kind === 'sheet') void loadSheet(viewer, what.status)
			else void send(viewer, what.question, what.key)
		}
	}

	const changeName = () => {
		forgetViewer()
		dispatch({ type: 'forget' })
	}

	const screen = state.screen
	const header = matchHeader(screen)
	return (
		<div className="layout">
			{/* Stands in for the viewer's own stream on a wide screen; the panel repeats everything in it. */}
			<div className="layout__stream" aria-hidden="true">
				<div className="layout__match">
					{header !== null && (
						<>
							<span className="layout__title">{header.title}</span>
							{header.clock !== null && <span className="layout__clock">{header.clock}</span>}
						</>
					)}
				</div>
				<div className="layout__screen">
					<StreamIcon />
					<p className="layout__screen-title">Your match: TV, stream or another tab</p>
					<p>Between the Lines never covers it. The panel sits beside it.</p>
				</div>
			</div>
			<main className="layout__panel">
				<header className="layout__brand">
					<h1 className="layout__name">
						Between <span className="layout__the">the</span> Lines
					</h1>
					{viewer !== null && screen.kind !== 'welcome' && (
						<button type="button" className="text-button" onClick={changeName}>
							Not {viewer}?
						</button>
					)}
				</header>
				<div className="layout__body">
					{screen.kind === 'welcome' && (
						<Welcome
							status={screen.status}
							error={screen.error}
							defaultName={screen.name}
							onStart={name => void start(name, false)}
							onWatch={() => {
								if (viewer !== null) void loadSheet(viewer, screen.status)
							}}
							onChangeName={changeName}
							onChangeTeam={() => {
								if (screen.status !== null) void loadPick(screen.status)
							}}
						/>
					)}
					{screen.kind === 'pick' && viewer !== null && (
						<PickTeam
							clubs={screen.clubs}
							chosen={screen.status.club?.team_id ?? null}
							suggested={screen.status.suggested_club}
							busy={screen.busy}
							onChoose={club => void choose(viewer, club)}
						/>
					)}
					{screen.kind === 'sheet' && viewer !== null && (
						<TeamSheet
							sheet={screen.sheet}
							canChangeTeam={screen.status?.can_choose_club ?? false}
							onKickOff={() => void loadNext(viewer)}
							onChangeTeam={() => {
								if (screen.status !== null) void loadPick(screen.status)
							}}
						/>
					)}
					{screen.kind === 'loading' && (
						<p className="layout__loading" role="status">
							{screen.message}
						</p>
					)}
					{screen.kind === 'step' && (
						<MatchStep
							home={screen.question.home}
							away={screen.question.away}
							matchNumber={screen.question.match_number}
							from={screen.from?.clock ?? null}
							to={screen.question.delivered}
							occurred={screen.question.occurred}
							score={
								screen.question.delivered.delivery === 'live'
									? (screen.question.context.score?.display ?? null)
									: null
							}
							yours={screen.question.your_team}
							onArrive={() => {
								dispatch({ type: 'open' })
							}}
						/>
					)}
					{screen.kind === 'question' && viewer !== null && (
						<>
							<QuestionSheet
								key={screen.question.pack_id}
								question={screen.question}
								busy={screen.busy}
								onLockIn={key => void send(viewer, screen.question, key)}
							/>
							<p className="layout__keys">
								<kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> or arrows to pick · <kbd>Enter</kbd> to lock in
							</p>
						</>
					)}
					{screen.kind === 'feedback' && viewer !== null && (
						<Feedback
							feedback={screen.feedback}
							question={screen.question}
							onContinue={() => void loadNext(viewer)}
						/>
					)}
					{screen.kind === 'full_time' && viewer !== null && (
						<FullTime
							summary={screen.summary}
							onNext={() => void (screen.summary.finished ? loadStatus(viewer) : loadSheet(viewer, null))}
						/>
					)}
					{screen.kind === 'error' && (
						<ErrorPanel
							message={screen.message}
							onRetry={() => {
								retry(screen.retry)
							}}
						/>
					)}
				</div>
			</main>
		</div>
	)
}

const StreamIcon = () => (
	<svg className="layout__screen-icon" viewBox="0 0 24 24" aria-hidden="true">
		<rect x="2" y="5" width="20" height="13" rx="2" />
		<path d="M8 21h8" />
	</svg>
)

export default App
