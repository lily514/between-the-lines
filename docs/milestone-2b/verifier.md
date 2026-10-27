# The Verifier

A model writes the wording of questions and feedback; plain code decides whether the viewer sees it. The Verifier (`backend/src/btl/tutor/verifier.py`) checks every piece of wording against the evidence pack. If any check fails, the model is asked once to repair its text, and then the template is used instead.

The model never writes a number or a name itself. It writes **slots**, such as `{answer.threat_added}`, and code fills them from the pack. Most checks follow from that: anything that looks like a fact but isn't in a slot is something the model made up.

The Verifier is strict on purpose. A false rejection costs one template sentence. A false acceptance puts a wrong claim in front of someone learning the game.

Every check below has a name. The name is the reason given in the logs, in the repair request to the model, and in the evaluation table.

The examples come from a pass question ("Where should the pass go?") unless they say otherwise.

## slots

**Rule:** every slot names a fact the text may use. A question may use only what the viewer can know before answering (`question_values`); feedback may use the whole pack (`feedback_values`).

- Rejected question: "{player} has the ball for {team}. Can they find {receiver}?" The receiver is the answer, so it isn't in the question's facts.
- Rejected feedback: "… {not_a_fact}". There is no such fact.
- Rejected: "Was he past the {second-last defender}?" Braces that don't make a slot would reach the viewer as they are.

## bare_number

**Rule:** no digits and no number words outside slots. Every number comes from the pack.

Number words are "two" to "ninety", "hundred", "thousand", "million", "dozen", "half", "quarter", "twice", "double", "triple", and the ordinals "second" to "tenth". "One", "first", "last" and "once" aren't on the list, because they are nearly always a pronoun or an adverb ("this one", "drop back first", "at once").

Football phrases that contain number words are allowed whole: "second-last defender", "half-time", "halfway", "first half", "second half", a side's half ("their own half", "the other team's half"), and the thirds of the pitch ("own third", "middle third", "attacking third", "defensive third", "final third").

- Rejected: "… with 3 defenders close." and "… with two defenders close."
- Passes: "{player} has the ball for {team} in their own half, just before half-time."

## names

**Rule:** read with the slots filled in, a capitalised word that doesn't start a sentence (or a clause after a colon) must appear in one of the pack's facts, which is where the clubs and players come from. A short allowlist adds "Expected Threat", "Laws of the Game" and "VAR". This catches real clubs and players, and names the model invents.

- Rejected: "… against Gortham Rovers." Gortham Rovers isn't in the match.

## vocabulary

**Rule:** no betting words: odds, bet, wager, stake, tip, punt, bookmaker, bookie, accumulator, gamble.

- Rejected: "What are the odds of a pass forward?"

## hint (questions only)

**Rule:** a question must not point at an option, in any of three ways:

- **By letter:** "option B", "(C)", "B)", or a lone B or C.
- **By an option's slot:** `{B.label}`.
- **By a word from an option's label that tells the options apart:** a word in some labels but not all, which the question doesn't otherwise show.

  Words that join a label together ("to", "the", "when", "their", "your") don't count, and neither do words any football question uses ("ball", "back", "play", "stopped", "referee").

- Rejected: "Should the pass go to {B.label}?" and "Is option B the pass?"
- Rejected, for a restart: "The ball has gone over the {out_line}, last touched by {last_touch_team}. Is it a corner?" "Corner" is in one option's label.

## verdict (feedback only)

**Rule:** no verdict phrases: "correct", "wrong", "well done", "not quite", "spot on", "unlucky", "good call" and the like. The verdict ("Right read." or "Good instinct, not this one.") comes from the grade, written by code, so it can never contradict the answer.

- Rejected: "Correct: the pass to {answer.target} …"

## grounded (feedback only)

**Rule:** the explanation cites the answer (`{answer}` or an `{answer.*}` fact) and at least one of the pack's outcome facts. After a wrong pick in a pass question, it also cites a `{chosen.*}` fact, so the viewer hears how their pass compared.

The rule is the same for every kind of question, because every pack has an answer and outcome facts: lines broken for a pass, `restart_team` for a restart, `margin_m` and `offside_call` for offside, `box_position` and `foul_outcome` for a foul.

- Rejected: "It went through {lines_broken} lines, against {chosen.threat_added}." It never says what the answer was.
- Rejected: "The answer was {answer}, not {chosen}." It cites no outcome.
- Rejected after a wrong pass: "The pass to {answer.target} changed the chance by {answer.threat_added}." The viewer's own pick is missing.

## comparison (feedback only)

**Rule:** a sentence that names the same fact for two options ("{answer.threat_added}" and "{chosen.threat_added}") and compares them must order them as the values do. "More", "higher", "wider" and the like mean the first is bigger; "fewer", "less", "lower" mean it is smaller.

A comparison code can't check ("better", "faster", or "than" without "more" or "fewer") is rejected.

- Passes: "{answer.threat_added} is more than {chosen.threat_added}." when the right pass added more threat.
- Rejected: "{chosen.threat_added} is more than {answer.threat_added}." The facts say otherwise.
- Rejected: "{answer.threat_added} is better than {chosen.threat_added}."

## misconception (feedback only)

**Rule:** after a wrong answer the model may pick one of the concept's common mix-ups by its number, which must exist. After a right answer it must pick none.

## echo

**Rule:** read with the slots filled in, the text must not:
- say the same words twice in a row within a clause (a comma ends a clause, so "shots, shots on target" is fine);
- write out a name or phrase in the same sentence as its own slot;
- use a whole-sentence fact (such as `{foul_outcome}`, "Hexham Anchors get a free kick.") inside another sentence.

This check came from the first live tries with the model (see the implementation notes, T3). It often wrote a slot and then its value, or placed a phrase-valued slot next to the same phrase.

- Rejected: "… was {beyond_or_behind} the second-last defender", which reads "behind the second-last defender the second-last defender".
- Rejected: "… to {restart_team} (Ripon Wardens)."
- Rejected: "The answer was {answer}, since {foul_outcome} and that was all."

## length

**Rule:**
- A question has at most 45 words.
- An explanation has at most 90 words.
- A takeaway is one sentence of at most 25 words.

A slot counts as one word.

## What the Verifier can't check

Whether an explanation is *true* football, and whether it suits the viewer's level. A sentence can pass every check and still get a Law wrong. The evaluation's hand review covers that, and the README lists it among the honest limits.

## The templates pass too

The template Tutor is the fallback, so its wording must pass every check. A test runs it over 40 seeds: every concept, every kind of question, every level, asked live and later, after a right and a wrong pick.
