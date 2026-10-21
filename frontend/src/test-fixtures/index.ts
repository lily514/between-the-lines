// Real payloads captured from the API (seed 7's matches), for tests. JSON imports type pairs as number[] rather than
// [number, number], so each is cast once here.
import type { Feedback, Question, TeamSheet } from '../api/client.ts'
import counterFeedbackJson from './counter-feedback.json'
import counterQuestionJson from './counter-question.json'
import identifyFeedbackJson from './identify-feedback.json'
import identifyQuestionJson from './identify-question.json'
import predictFeedbackJson from './predict-feedback.json'
import predictQuestionJson from './predict-question.json'
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
	next_stage: "Get to level 3 in any concept to see players' numbers from matches you've watched.",
	teams: sheetStage3.teams.map(team => ({
		...team,
		matches_watched: null,
		players: team.players.map(player => ({ ...player, numbers: null }))
	}))
}
