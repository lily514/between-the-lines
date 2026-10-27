"""The templated Tutor: plain, safe wording written in code.

It is the Tutor for Milestone 2a, and later the fallback whenever a model's wording fails a
check. Every number reaches the viewer through a slot, so its text can always be verified.

Questions are worded by what they ask. A question asked after the play opens by saying when it
happened. Feedback uses the concept map's explanation at the viewer's level (beginner,
intermediate or analyst), then gives the answer with the outcome fact that settles it (for a pass,
compared with the viewer's pick), and offers a common misconception when the answer was wrong.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from btl.learn.evidence import EvidencePack, QuestionView, Timing
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.base import NO_HISTORY, History, TutorFeedback, TutorQuestion
from btl.tutor.slots import slot_names

SOURCE = "template"
# What each question asks, in words. Every slot here is in the question view.
ASKING: Mapping[Asks, str] = {
    Asks.WHERE_TO_PASS: "{player} has the ball for {team}. Where should the pass go?",
    Asks.LINES_BROKEN: "{player} has just played the ball forward for {team}. "
    "How many defensive lines did that pass go through?",
    Asks.GAP_WIDTH: "{player}'s pass went through a gap in a defensive line. How wide was the gap?",
    Asks.WHAT_THEY_DID: "{team} lost the ball to {opponent}. What did they do next?",
    Asks.SECONDS_TO_REGAIN: "{team} lost the ball to {opponent} and won it back. "
    "How long did that take?",
    Asks.WHAT_RESTART: "The ball has gone over the {out_line}, last touched by {last_touch_team}. "
    "What happens now?",
    Asks.FLAG_OR_NOT: "{player} is about to pass to {attacker}. Will the flag go up?",
    Asks.WHO_IS_OFFSIDE: "Which of these attackers is in an offside position as {player} "
    "plays the pass?",
    Asks.WAS_IT_OFFSIDE: "{player} passed to {attacker}. Was {attacker} offside when the pass "
    "was played?",
    Asks.AFTER_THE_FOUL: "{fouler} has fouled a {fouled_team} player. What happens now?",
    Asks.WHY_BOOKED: "{fouler} has been booked for fouling a {fouled_team} player. Why?",
    Asks.WHY_PLAY_ON: "{fouler} fouled a {fouled_team} player, but the referee let play go on. "
    "Why?",
    Asks.HOW_WON: "{team} have just taken the ball off {opponent}. How did they win it?",
    Asks.WHERE_WON: "{team} have just taken the ball off {opponent}. Where on the pitch did they "
    "win it?",
    Asks.WHY_WHERE_MATTERS: "{team} have the ball back from {opponent}. Why does where they took "
    "it matter?",
}
# How a question asked after the play opens, by where play is when it is asked.
LOOKING_BACK: Mapping[str, str] = {
    "dead ball": "Play has stopped for a {restart}. Back at {occurred_at}: ",
    "half-time": "Half-time. Back at {occurred_at}: ",
    "full time": "Full time. Back at {occurred_at}: ",
}
LEVEL_NAMES = {1: "beginner", 2: "intermediate", 3: "analyst"}
# After a wrong pick in a predict question: why the right pass was better, measured.
COMPARE_PASSES = (
    "The pass to {answer.target} went through the gap: it went through {answer.lines_broken} "
    "of the defending team's lines and changed the chance of scoring soon by "
    "{answer.threat_added}, against {chosen.threat_added} for the pass to {chosen.target}."
)
CONFIRM_PASS = (
    "The pass to {answer.target} went through {answer.lines_broken} of the defending team's "
    "lines and changed the chance of scoring soon by {answer.threat_added}."
)
CORRECT_CHOICE = "The answer was {answer}."
# After any other question, the outcome fact that settles it, unless the explanation already
# cites one.
SETTLED_BY: Mapping[Asks, str] = {
    Asks.LINES_BROKEN: "The pass went through {lines_broken} of the defending team's lines.",
    Asks.GAP_WIDTH: "The gap was {gap_m} m wide.",
    Asks.WHAT_THEY_DID: "{player} won the ball back {seconds_to_regain} seconds after it was lost.",
    Asks.SECONDS_TO_REGAIN: "{player} won the ball back {seconds_to_regain} seconds after it was "
    "lost.",
    Asks.WHAT_RESTART: "It was a {restart_type} to {restart_team}.",
    Asks.FLAG_OR_NOT: "{attacker} was {margin_m} m {beyond_or_behind} when the pass was played, "
    "so the call was {offside_call}.",
    Asks.WHO_IS_OFFSIDE: "{attacker} was {margin_m} m {beyond_or_behind} when the pass was played.",
    Asks.WAS_IT_OFFSIDE: "{attacker} was {margin_m} m {beyond_or_behind} when the pass was "
    "played, so the call was {offside_call}.",
    Asks.AFTER_THE_FOUL: "{foul_outcome} {booking_note}",
    Asks.WHY_BOOKED: "{booking_note}",
    Asks.WHY_PLAY_ON: "{foul_outcome}",
    Asks.HOW_WON: "{player} won it by {recovery_type}, in the {pitch_third}.",
    Asks.WHERE_WON: "{player} won it {metres_from_own_goal} m from their own goal line, in the "
    "{pitch_third}.",
    Asks.WHY_WHERE_MATTERS: "{player} won it in the {pitch_third}; {team} have won it in the "
    "attacking third {high_recoveries} times so far, against a match average of "
    "{avg_high_recoveries}.",
}


@dataclass(frozen=True, slots=True)
class TemplateTutor:
    """A `btl.tutor.base.Tutor` whose wording is fixed templates with fact slots."""

    source: str = field(default=SOURCE, init=False)

    def question(self, view: QuestionView) -> TutorQuestion:
        """The question for what it asks, opening with when it happened if asked later."""
        return TutorQuestion(_looking_back(view.timing) + ASKING[view.asks])

    def feedback(
        self, pack: EvidencePack, grade: Grade, history: History = NO_HISTORY
    ) -> TutorFeedback:
        """The concept's explanation at the viewer's level, the comparison, and a misconception.

        The viewer's history is ignored: the same pick always gets the same words.

        The verdict ("Right read." or "Good instinct, not this one.") comes from the grade,
        not from here.
        """
        explanation = _explanation(pack)
        sentences = [explanation]
        if pack.asks is Asks.WHERE_TO_PASS:
            sentences.append(CONFIRM_PASS if grade.correct else COMPARE_PASSES)
        else:
            sentences.append(CORRECT_CHOICE)
            if not slot_names(explanation) & set(pack.outcome):
                sentences.append(SETTLED_BY[pack.asks])
        return TutorFeedback(
            explanation=" ".join(sentences),
            takeaway=pack.concept.objective,
            source=self.source,
            misconception=None if grade.correct else _misconception(pack),
        )


def _looking_back(timing: Timing) -> str:
    if timing.delivery == "live":
        return ""
    opening = LOOKING_BACK[timing.delivered_phase]
    return opening if "{restart}" not in opening or timing.restart else "Play has stopped. "


def _explanation(pack: EvidencePack) -> str:
    texts = {
        "beginner": pack.concept.beginner,
        "intermediate": pack.concept.intermediate,
        "analyst": pack.concept.analyst,
    }
    return texts[LEVEL_NAMES[pack.level]]


def _misconception(pack: EvidencePack) -> str:
    """One of the concept's misconceptions, the same one every time for the same pack."""
    misconceptions = pack.concept.misconceptions
    return misconceptions[int(pack.pack_id, 16) % len(misconceptions)]
