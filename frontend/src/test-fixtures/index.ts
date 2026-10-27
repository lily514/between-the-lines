// Real payloads captured from the API (seed 7's matches), for tests. JSON imports type pairs as number[] rather than
// [number, number], so each is cast once here. The questions' `play_by_play` was written by hand to fit their clocks,
// as the matches have changed since they were captured.
import type { BeforeMatch, ConceptMap, Feedback, MatchSummary, Question, Report, TeamSheet } from '../api/client.ts'
import beforeMatchFirstLookJson from './before-match-first-look.json'
import beforeMatchLevelUpJson from './before-match-level-up.json'
import conceptMapJson from './concept-map.json'
import counterFeedbackJson from './counter-feedback.json'
import counterQuestionJson from './counter-question.json'
import curriculumJson from './curriculum.json'
import identifyFeedbackJson from './identify-feedback.json'
import identifyQuestionJson from './identify-question.json'
import matchesJson from './matches.json'
import matchesInProgressJson from './matches-in-progress.json'
import predictFeedbackJson from './predict-feedback.json'
import predictQuestionJson from './predict-question.json'
import reportFullTimeJson from './report-full-time.json'
import reportHalftimeJson from './report-halftime.json'
import sheetStage1Json from './sheet-stage-1.json'
import sheetStage3Json from './sheet-stage-3.json'

/** A live predict question ("where should the pass go?") and its feedback after a wrong pick. */
export const predictQuestion = predictQuestionJson as unknown as Question
export const predictFeedback = predictFeedbackJson as unknown as Feedback
/** A review question about lines broken, asked at a dead ball, and its feedback after a right pick. */
export const identifyQuestion = identifyQuestionJson as unknown as Question
export const identifyFeedback = identifyFeedbackJson as unknown as Feedback
/** A review question about a counter-press ("what did they do next?") and its feedback after a wrong pick. */
export const counterQuestion = counterQuestionJson as unknown as Question
export const counterFeedback = counterFeedbackJson as unknown as Feedback
/** A new viewer's team sheet (stage 1): Ripon Wardens, their team, at home. */
export const sheetStage1 = sheetStage1Json as unknown as TeamSheet
/** Match 3 for a Hexham Anchors fan who has watched two matches (stage 3): numbers for their team, none for the
 * opponent they haven't seen. */
export const sheetStage3 = sheetStage3Json as unknown as TeamSheet
/** The same sheet at stage 2: formations and kick-off spots, no numbers. */
export const sheetStage2: TeamSheet = {
	...sheetStage3,
	stage: 2,
	next_stage: "Get to Sharp in any concept to see players' numbers from matches you've watched.",
	teams: sheetStage3.teams.map(team => ({
		...team,
		matches_watched: null,
		players: team.players.map(player => ({ ...player, numbers: null }))
	}))
}

/** The curriculum before there is a viewer: all 20 concepts, eight asked about now, no values. */
export const curriculum = curriculumJson as unknown as ConceptMap
/** A Ripon Wardens fan's map after match 1: levels on the eight concepts asked about now. */
export const conceptMap = conceptMapJson as unknown as ConceptMap
/** The same fan's matches with two answers in match 1: it is in progress, 0–0 at the last answer. */
export const matchesInProgress = matchesInProgressJson as unknown as MatchSummary[]
/** The same fan's matches after match 1: finished 1–0 to them, match 2 next. */
export const matchesAfterOne = matchesJson as unknown as MatchSummary[]
/** Match 1's scouting reports for that fan, at halftime and full time. */
export const reportHalftime = reportHalftimeJson as unknown as Report
export const reportFullTime = reportFullTimeJson as unknown as Report

/** Before match 2 for the Ripon Wardens fan: Line-breaking passes rose to Solid, so Who's playing shows formations. */
export const beforeMatchLevelUp = beforeMatchLevelUpJson as unknown as BeforeMatch
/** Before match 1 for a viewer from before Milestone 5: a First look at the three concepts new to them. */
export const beforeMatchFirstLook = beforeMatchFirstLookJson as unknown as BeforeMatch
/** Before a match with nothing new: straight on to Who's playing. */
export const beforeMatchNothing: BeforeMatch = { ...beforeMatchLevelUp, level_ups: [], unlock_note: null }
