// Real payloads captured from the API (seed 7's matches), for tests. JSON imports type pairs as number[] rather than
// [number, number], so each is cast once here.
import type { Feedback, Question } from '../api/client.ts'
import counterFeedbackJson from './counter-feedback.json'
import counterQuestionJson from './counter-question.json'
import identifyFeedbackJson from './identify-feedback.json'
import identifyQuestionJson from './identify-question.json'
import predictFeedbackJson from './predict-feedback.json'
import predictQuestionJson from './predict-question.json'

/** A live predict question ("where should the pass go?") and its feedback after a wrong pick. */
export const predictQuestion = predictQuestionJson as unknown as Question
export const predictFeedback = predictFeedbackJson as unknown as Feedback
/** A review question about lines broken, asked at a dead ball, and its feedback after a right pick. */
export const identifyQuestion = identifyQuestionJson as unknown as Question
export const identifyFeedback = identifyFeedbackJson as unknown as Feedback
/** A review question about a counter-press ("what did they do next?") and its feedback after a wrong pick. */
export const counterQuestion = counterQuestionJson as unknown as Question
export const counterFeedback = counterFeedbackJson as unknown as Feedback
