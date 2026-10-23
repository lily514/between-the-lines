import { useCallback, useEffect, useLayoutEffect, useReducer, useRef, useState, type CSSProperties } from 'react'
import {
	answer,
	ApiError,
	chooseClub,
	getClubs,
	getConceptMap,
	getMatches,
	getStatus,
	getTeamSheet,
	nextStep,
	startViewer,
	type ConceptMap,
	type Question,
	type Status
} from '../api/client.ts'
import './App.css'
import {
	forgetViewer,
	initialState,
	LOADING_CLUBS,
	LOADING_MATCHES,
	LOADING_NEXT,
	LOADING_SHEET,
	LOADING_START,
	matchHeader,
	needsClub,
	newViewerId,
	offersMap,
	reducer,
	rememberedViewer,
	rememberViewer,
	type Retry
} from './App.support.ts'
import CurriculumMap from './CurriculumMap/index.tsx'
import ErrorPanel from './Shared/ErrorPanel.tsx'
import Header from './Shared/Header.tsx'
import PanelHandle from './Shared/PanelHandle.tsx'
import { PANEL_DEFAULT, rememberedPanelWidth, rememberPanelWidth } from './Shared/PanelHandle.support.ts'
import Feedback from './Feedback/index.tsx'
import FullTime from './FullTime/index.tsx'
import Matches from './Matches/index.tsx'
import MatchStep from './MatchStep/index.tsx'
import PickTeam from './PickTeam/index.tsx'
import QuestionSheet from './QuestionSheet/index.tsx'
import TeamSheet from './TeamSheet/index.tsx'
import Welcome from './Welcome/index.tsx'

const messageOf = (error: unknown) =>
	error instanceof Error ? error.message : 'The server could not be reached. Check it is running, then try again.'

/** The learning loop in the browser: a start, then Matches as home base, and each match as a run of questions,
 * feedback and a full-time summary. The curriculum map opens over any screen from the header.
 *
 * On a wide screen the companion sits in a side panel beside the viewer's own stream, and never covers it. The viewer
 * can drag the panel wider; null keeps the usual width from tokens.css. */
const App = () => {
	const [remembered] = useState(rememberedViewer)
	const [state, dispatch] = useReducer(reducer, remembered, initialState)
	const viewer = state.viewer
	const [panelWidth, setPanelWidth] = useState(rememberedPanelWidth)
	const [curriculum, setCurriculum] = useState<ConceptMap | null>(null)
	const panel = useRef<HTMLElement>(null)
	const mapButton = useRef<HTMLButtonElement>(null)
	// Where the screen under the map was scrolled to, so closing the map puts the viewer back exactly there.
	const scrolled = useRef<{ page: number; panel: number } | null>(null)

	const fail = useCallback((error: unknown, retry: Retry) => {
		if (error instanceof ApiError && error.status === 404) {
			forgetViewer()
			dispatch({ type: 'forget', message: 'That record has gone, so you are starting afresh.' })
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

	const loadMatches = useCallback(
		async (id: string) => {
			dispatch({ type: 'loading', message: LOADING_MATCHES })
			try {
				const [status, matches] = await Promise.all([getStatus(id), getMatches(id)])
				dispatch({ type: 'matches', status, matches })
			} catch (error) {
				fail(error, { kind: 'matches' })
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
				await chooseClub(id, club)
				await loadMatches(id)
			} catch (error) {
				// 409: the viewer has started watching (in another tab, say), so their team is settled.
				if (error instanceof ApiError && error.status === 409) {
					await loadMatches(id)
				} else {
					fail(error, { kind: 'choose', club })
				}
			}
		},
		[fail, loadMatches]
	)

	const start = useCallback(
		async (id: string) => {
			dispatch({ type: 'loading', message: LOADING_START })
			try {
				const status = await startViewer(id)
				rememberViewer(status.viewer_id)
				if (needsClub(status)) {
					await loadPick(status)
				} else {
					await loadMatches(status.viewer_id)
				}
			} catch (error) {
				// 422: the id kept in this browser isn't one the API accepts (edited by hand, say), so start afresh.
				if (error instanceof ApiError && error.status === 422) {
					forgetViewer()
					dispatch({ type: 'rejected', message: error.message })
				} else {
					fail(error, { kind: 'start', viewer: id })
				}
			}
		},
		[fail, loadMatches, loadPick]
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

	// A remembered viewer comes back to Matches, where they can rejoin a match part-way through.
	const resumed = useRef(false)
	useEffect(() => {
		if (remembered !== null && !resumed.current) {
			resumed.current = true
			void start(remembered)
		}
	}, [remembered, start])

	// The first screen says what the questions cover, from the curriculum; without it, it still works.
	const onWelcome = state.screen.kind === 'welcome'
	useEffect(() => {
		if (onWelcome && curriculum === null) {
			getConceptMap(null).then(setCurriculum, () => undefined)
		}
	}, [onWelcome, curriculum])

	const openMap = async () => {
		scrolled.current = { page: window.scrollY, panel: panel.current?.scrollTop ?? 0 }
		dispatch({ type: 'map', map: null })
		try {
			dispatch({ type: 'map', map: await getConceptMap(viewer) })
		} catch (error) {
			dispatch({ type: 'map', map: null, error: messageOf(error) })
		}
	}

	const closeMap = useCallback(() => {
		dispatch({ type: 'close' })
	}, [])

	// Closing the map puts the screen back as it was: the same scroll, and focus on the button that opened it.
	const mapOpen = state.overlay !== null
	useLayoutEffect(() => {
		if (mapOpen || scrolled.current === null) return
		window.scrollTo(0, scrolled.current.page)
		if (panel.current !== null) panel.current.scrollTop = scrolled.current.panel
		scrolled.current = null
		mapButton.current?.focus()
	}, [mapOpen])

	const retry = (what: Retry) => {
		if (what.kind === 'start') {
			void start(what.viewer)
		} else if (viewer !== null) {
			if (what.kind === 'next') void loadNext(viewer)
			else if (what.kind === 'matches') void loadMatches(viewer)
			else if (what.kind === 'pick') void loadPick(what.status)
			else if (what.kind === 'choose') void choose(viewer, what.club)
			else if (what.kind === 'sheet') void loadSheet(viewer, what.status)
			else void send(viewer, what.question, what.key)
		}
	}

	const startOver = () => {
		forgetViewer()
		dispatch({ type: 'forget' })
	}

	const settlePanel = (width: number | null) => {
		setPanelWidth(width)
		rememberPanelWidth(width)
	}

	const screen = state.screen
	const header = matchHeader(screen)
	const layoutStyle = panelWidth === null ? undefined : ({ '--panel-w': `${String(panelWidth)}px` } as CSSProperties)
	return (
		<div className="layout" style={layoutStyle}>
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
			<PanelHandle
				width={panelWidth ?? PANEL_DEFAULT}
				onResize={setPanelWidth}
				onSettle={settlePanel}
				onReset={() => {
					settlePanel(null)
				}}
			/>
			<main ref={panel} className="layout__panel">
				<Header
					showMap={offersMap(state)}
					mapOpen={mapOpen}
					mapButton={mapButton}
					onMap={() => {
						if (mapOpen) closeMap()
						else void openMap()
					}}
				/>
				{state.overlay?.kind === 'map' && (
					<div className="layout__body">
						<CurriculumMap map={state.overlay.map} error={state.overlay.error} onBack={closeMap} />
					</div>
				)}
				<div className="layout__body" hidden={mapOpen}>
					{screen.kind === 'welcome' && (
						<Welcome
							curriculum={curriculum}
							error={screen.error}
							onStart={() => void start(newViewerId())}
							onSeeAll={() => void openMap()}
						/>
					)}
					{screen.kind === 'matches' && viewer !== null && (
						<Matches
							status={screen.status}
							matches={screen.matches}
							onWatch={() => void loadSheet(viewer, screen.status)}
							onRejoin={() => void loadNext(viewer)}
							onChangeTeam={() => void loadPick(screen.status)}
							onStartOver={startOver}
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
							score={`${String(screen.question.score.home)}–${String(screen.question.score.away)}`}
							catchUp={screen.question.catch_up}
							yours={screen.question.your_team}
							onArrive={() => {
								dispatch({ type: 'open' })
							}}
						/>
					)}
					{(screen.kind === 'step' || screen.kind === 'feedback') && viewer !== null && (
						<p className="layout__done">
							<button type="button" className="text-button" onClick={() => void loadMatches(viewer)}>
								Done for this match
							</button>
						</p>
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
						<FullTime summary={screen.summary} onNext={() => void loadMatches(viewer)} />
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
