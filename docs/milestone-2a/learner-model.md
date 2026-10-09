# The learner model

How Between the Lines decides how well a viewer understands each football concept, and why every change to that number can be explained in one sentence.

## The idea: Bayesian Knowledge Tracing

Bayesian Knowledge Tracing (BKT) treats each concept as a hidden yes-or-no: does this viewer understand line-breaking passes, or not? We can't see the answer directly, only their answers to questions. So BKT keeps a probability, **mastery**, that the answer is yes, and updates it after every question in two steps.

**Step 1: what the answer says.** A viewer who understands the concept usually answers correctly, but can **slip** (misread the picture, tap the wrong option). A viewer who doesn't can still **guess** right. Bayes' rule compares how likely this answer was from each kind of viewer and shifts mastery towards the more likely one.

**Step 2: what the feedback teaches.** Every answer is followed by an explanation, so there is a chance the viewer **learns** the concept right then, whatever they answered.

## The four numbers

| Parameter | Meaning | Where it comes from |
|---|---|---|
| prior | Mastery before any question | The concept map, by tier: 0.40 for tier 0 down to 0.05 for tier 3 |
| learn | Chance the feedback teaches it | The concept map, by tier |
| slip | Chance someone who knows it still answers wrongly | The concept map: 0.10 everywhere |
| guess | Chance a pure guess is right | The question: 1 / number of options, so 1/3 with three options |

`guess` isn't tuned at all; it follows from the question. A concept can override any of the other three in the concept map.

## A worked example

Line-breaking passes are tier 2: prior 0.15, learn 0.15, slip 0.10. Each question has three options, so guess = 1/3.

The viewer answers the first question correctly.
- **If they understand it**, a right answer had probability 0.9 (no slip). Weighted by the prior: 0.15 × 0.9 = 0.135.
- **If they don't**, it had probability 1/3 (a lucky guess). Weighted: 0.85 × 1/3 ≈ 0.283.
- After the answer, mastery is 0.135 / (0.135 + 0.283) ≈ **0.32**.
- After the feedback, there's a 0.15 chance they learned it: 0.32 + 0.68 × 0.15 ≈ **0.42**.

Four right answers in a row give 0.15 → 0.42 → 0.72 → 0.89 → 0.96. The concept counts as mastered above 0.95, so four in a row is enough. This sequence is a test (`test_four_right_answers_climb_as_the_plan_worked_out`).

**A wrong answer can still raise mastery** when it was low. From 0.15, a wrong answer drops it to about 0.03 in step 1. The learning step then adds 0.97 × 0.15, giving about 0.17, slightly *up*. That isn't a bug: having just seen the explanation, the viewer is a little more likely to understand than before. The explanation sentence says exactly that.

## The one-sentence explanations

Every update produces a sentence quoting its own numbers, for the viewer and for judges:

> Right. A guess is right 1 time in 3, and someone who understands line-breaking passes still slips 10% of the time, so we're now 42% sure you understand it, up from 15%.

> Not this time. Someone who understands line-breaking passes slips only 10% of the time, so we're now 47% sure you understand it, down from 80%.

> Not this time, which on its own lowers our estimate for line-breaking passes. But you've just seen the explanation, and that teaches it 15% of the time, so we're now 17% sure you understand it, up from 15%.

## Swapping the model

BKT sits behind an interface, `KnowledgeModel` in `btl/learn/knowledge.py`, so another model can replace it. Performance Factors Analysis (PFA) is an example: it counts each viewer's right and wrong answers per concept and turns them into a probability with a logistic curve, instead of tracking a hidden yes-or-no.

- **The rest of the app only asks a model for `mastery(concept)` and its `thresholds`.** That covers the selector, the questions, the feedback and the progress bars.
- **Each answer is an `Observation`:** the concepts, whether it was right, the number of options, the moment's difficulty, the question's level, and whether it was asked live or deferred to a stoppage. BKT uses only rightness and the number of options. Another model can use the rest.
- **The viewer's answers are the source of truth.** A model's state is always what `replay` gives for the answers so far. Changing the model, or its parameters, means replaying the answers, never migrating stored numbers.
- **Every model must pass the same contract tests** (`tests/learn/test_knowledge.py`): mastery stays between 0 and 1, a right answer never lowers it, the same answers always give the same numbers, replaying equals updating one by one, and the explanation quotes the before and after numbers. A new model joins by adding one line to that file.
