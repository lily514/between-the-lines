# The AI Tutor: hand review

*Reviewed by Lily on 2026-10-22 as a scan, not box by box: accurate enough for the prototype, with nothing wrong about the match. See `tutor-evaluation.md`.*

For each sample, tick what holds, and note anything wrong. The facts are what the words may say; the template's wording is there for comparison.

### 1. Line-breaking passes: lines broken, level 1, live, question (first try)

**Model**

> At 00:32, #10 Chinedu Trankwo played the ball forward for Ludlow Ferrymen. Play is paused. For how many defensive lines did that pass go through, before reaching their forwards?

**Template**

> #10 Chinedu Trankwo has just played the ball forward for Ludlow Ferrymen. How many defensive lines did that pass go through?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:32; player = #10 Chinedu Trankwo
> Outcome: lines_broken = one; gap_m = 10; xt_before = 0.4%; xt_after = 0.63%; threat_added = +0.22%; receiver_zone = middle third
> Options: A: Two | B: None | C (right): One

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 2. Line-breaking passes: where to pass, level 2, live, question (first try)

**Model**

> It’s paused at 00:32. #10 Chinedu Trankwo has the ball for Ludlow Ferrymen. Where should you send the next line-breaking pass for best advantage against Hexham Anchors?

**Template**

> #10 Chinedu Trankwo has the ball for Ludlow Ferrymen. Where should the pass go?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:32; player = #10 Chinedu Trankwo
> Outcome: lines_broken = one; gap_m = 10; xt_before = 0.4%; xt_after = 0.63%; threat_added = +0.22%; receiver_zone = middle third; receiver = #7 Cheikh Okokunle
> Options: A (right): Pass to #7 Cheikh Okokunle | B: Pass to #5 Milan Hafkamp | C: Pass to #16 Stijn Schelinga

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 3. Line-breaking passes: lines broken, level 1, live, feedback after a right pick (first try)

**Model**

> That pass from #10 Chinedu Trankwo slid the ball behind the Hexham Anchors and skipped through one of their defending lines. That’s the key to line-breaking passing: it puts the receiver into space and can turn a stalemate into a real chance. With One, you should look for passes that cut through the line, not passes that just run straight at defenders.
> Takeaway: Spot line-breaking passes that slip behind defenders, because they create space and danger.

**Template**

> That pass skipped past several defenders at once. Getting the ball behind defenders is how teams create chances. The answer was One. The pass went through one of the defending team's lines.
> Takeaway: Spot passes that cut through a defensive line and explain why they create danger.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:32; player = #10 Chinedu Trankwo
> Outcome: lines_broken = one; gap_m = 10; xt_before = 0.4%; xt_after = 0.63%; threat_added = +0.22%; receiver_zone = middle third
> Options: A: Two | B: None | C (right): One

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 4. Line-breaking passes: where to pass, level 2, live, feedback after a right pick (first try)

**Model**

> Pass to #7 Cheikh Okokunle cuts through Hexham Anchors’ defensive line. This one broke one through a 10 m gap, so the receiver could run into the space between the lines. You also see the danger rise as +0.22% is added to the scoring chance soon, because defenders have to recover from the split line.
> Takeaway: Spot line-breaking passes and explain how the gap in the defence creates a forward threat.

**Template**

> A line-breaking pass cuts through a defensive line; this one broke one, through a gap 10 m wide. The receiver was standing in the space between the lines. The pass to #7 Cheikh Okokunle went through one of the defending team's lines and changed the chance of scoring soon by +0.22%.
> Takeaway: Spot passes that cut through a defensive line and explain why they create danger.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:32; player = #10 Chinedu Trankwo
> Outcome: lines_broken = one; gap_m = 10; xt_before = 0.4%; xt_after = 0.63%; threat_added = +0.22%; receiver_zone = middle third; receiver = #7 Cheikh Okokunle
> Options: A (right): Pass to #7 Cheikh Okokunle | B: Pass to #5 Milan Hafkamp | C: Pass to #16 Stijn Schelinga

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 5. Restarts: what restart, level 1, live, question (first try)

**Model**

> At 00:34, the ball went over the touchline and was last touched by Ludlow Ferrymen. With it out of play, what restart should happen now for Ludlow Ferrymen?

**Template**

> The ball has gone over the touchline, last touched by Ludlow Ferrymen. What happens now?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:34; player = #7 Cheikh Okokunle; last_touch_team = Ludlow Ferrymen; out_line = touchline
> Outcome: restart_type = throw-in; restart_team = Hexham Anchors
> Options: A: Corner to Hexham Anchors | B (right): Throw-in to Hexham Anchors | C: Throw-in to Ludlow Ferrymen

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 6. Restarts: what restart, level 1, deferred, question (first try)

**Model**

> Play is stopped for a goal kick at 00:34. You’re back at the touchline in front of Ludlow Ferrymen. The ball has gone over the touchline, last touched by Ludlow Ferrymen. What restart do you take now?

**Template**

> Play has stopped for a goal kick. Back at 00:34: The ball has gone over the touchline, last touched by Ludlow Ferrymen. What happens now?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:34; player = #7 Cheikh Okokunle; last_touch_team = Ludlow Ferrymen; out_line = touchline
> Outcome: restart_type = throw-in; restart_team = Hexham Anchors
> Options: A: Corner to Hexham Anchors | B (right): Throw-in to Hexham Anchors | C: Throw-in to Ludlow Ferrymen

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 7. Restarts: what restart, level 1, live, feedback after a right pick (first try)

**Model**

> When the ball goes out of play, the team that didn’t touch it last gets it back. Over the touchline that’s a throw-in. Here, it’s a throw-in to Hexham Anchors, labelled Throw-in to Hexham Anchors.
> Takeaway: Next time the ball goes out, name the restart type and the team that didn’t touch it last.

**Template**

> When the ball goes out, the team that didn't touch it last gets it back. Over a touchline that's a throw-in; over a goal line it's a corner or a goal kick. The answer was Throw-in to Hexham Anchors. It was a throw-in to Hexham Anchors.
> Takeaway: Say which restart comes next, and for which team, when the ball goes out of play.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:34; player = #7 Cheikh Okokunle; last_touch_team = Ludlow Ferrymen; out_line = touchline
> Outcome: restart_type = throw-in; restart_team = Hexham Anchors
> Options: A: Corner to Hexham Anchors | B (right): Throw-in to Hexham Anchors | C: Throw-in to Ludlow Ferrymen

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 8. Restarts: what restart, level 1, live, feedback after a wrong pick (first try)

**Model**

> When the ball goes out of play, the team that didn’t touch it last gets the restart. Over the touchline that’s a throw-in, not a corner. Here, the restart is throw-in to Hexham Anchors, which matches Throw-in to Hexham Anchors. You picked Corner to Hexham Anchors, which would be used for a different out-of-play line, like over the goal line.
> Takeaway: Next time it goes out on the touchline, give it as a throw-in to the team that didn’t touch it last.
> Common mix-up: The team that kicked it out gets the throw-in.

**Template**

> When the ball goes out, the team that didn't touch it last gets it back. Over a touchline that's a throw-in; over a goal line it's a corner or a goal kick. The answer was Throw-in to Hexham Anchors. It was a throw-in to Hexham Anchors.
> Takeaway: Say which restart comes next, and for which team, when the ball goes out of play.
> Common mix-up: If the attacking team kicks it over the goal line, they get a corner.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 00:34; player = #7 Cheikh Okokunle; last_touch_team = Ludlow Ferrymen; out_line = touchline
> Outcome: restart_type = throw-in; restart_team = Hexham Anchors
> Options: A: Corner to Hexham Anchors | B (right): Throw-in to Hexham Anchors | C: Throw-in to Ludlow Ferrymen

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 9. Counter-pressing: what they did, level 1, live, question (first try)

**Model**

> At 01:40, Ludlow Ferrymen lost the ball to Hexham Anchors. Play pauses right after—what did they do next? Think about their immediate response in transition play.

**Template**

> Ludlow Ferrymen lost the ball to Hexham Anchors. What did they do next?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:40
> Outcome: seconds_to_regain = 3.2; metres_from_goal = 22.3; pressers = one; player = #7 Cheikh Okokunle
> Options: A: Stopped the attack with a foul | B (right): Hunted the ball straight back and won it | C: Dropped back into their shape

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 10. Counter-pressing: seconds to win back, level 2, live, question (first try)

**Model**

> Hexham Anchors lost the ball to Hexham Anchors and Ludlow Ferrymen won it back. When play pauses at 01:40, how many seconds did that counter-pressing take to win it back?

**Template**

> Ludlow Ferrymen lost the ball to Hexham Anchors and won it back. How long did that take?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:40
> Outcome: seconds_to_regain = 3.2; metres_from_goal = 22.3; pressers = one; player = #7 Cheikh Okokunle
> Options: A: Under 2 s | B (right): 2 to 3.5 s | C: 3.5 s or more

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 11. Counter-pressing: what they did, level 1, live, feedback after a right pick (first try)

**Model**

> After losing the ball, Ludlow Ferrymen hunted it straight back instead of retreating. That Hunted the ball straight back and won it is counter-pressing: you win it back 3.2 seconds after it was lost, before the opponent can spread out. #7 Cheikh Okokunle helped apply the pressure from close range, starting the attack again quickly.
> Takeaway: Look for counter-pressing: win the ball straight back after losing it, before the opponent can organise.

**Template**

> After losing the ball, Ludlow Ferrymen hunted it straight back instead of retreating. Winning it back quickly catches the opponent before they can spread out. The answer was Hunted the ball straight back and won it. #7 Cheikh Okokunle won the ball back 3.2 seconds after it was lost.
> Takeaway: Recognize a counter-press: winning the ball straight back after losing it, before the opponent can organize.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:40
> Outcome: seconds_to_regain = 3.2; metres_from_goal = 22.3; pressers = one; player = #7 Cheikh Okokunle
> Options: A: Stopped the attack with a foul | B (right): Hunted the ball straight back and won it | C: Dropped back into their shape

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 12. Counter-pressing: seconds to win back, level 2, live, feedback after a right pick (first try)

**Model**

> You saw Ludlow Ferrymen win the ball back 3.2 seconds after losing it, with one player close to the ball. That quick regain is what you want to spot in a counter-press: the opponent is still turning to play forward, so the threat is stopped before they can organise. The timeframe you picked matches 2 to 3.5 s.
> Takeaway: Spot counter-presses by watching for a fast ball recovery before the opponent can organise.

**Template**

> Ludlow Ferrymen won the ball back 3.2 seconds after losing it, with one players close to the ball. A counter-press works as a group, while the opponent is still turning to play forward. The answer was 2 to 3.5 s.
> Takeaway: Recognize a counter-press: winning the ball straight back after losing it, before the opponent can organize.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:40
> Outcome: seconds_to_regain = 3.2; metres_from_goal = 22.3; pressers = one; player = #7 Cheikh Okokunle
> Options: A: Under 2 s | B (right): 2 to 3.5 s | C: 3.5 s or more

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 13. Offside: flag or not, level 1, live, question (first try)

**Model**

> In the transition at 01:46, #10 Chinedu Trankwo is about to pass to #9 Ibrahim Nwarafor. It’s paused for an offside check—will the flag go up?

**Template**

> #10 Chinedu Trankwo is about to pass to #9 Ibrahim Nwarafor. Will the flag go up?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:46; player = #10 Chinedu Trankwo; attacker = #9 Ibrahim Nwarafor
> Outcome: margin_m = 2.6; beyond_or_behind = behind the second-last defender; offside_call = onside
> Options: A: No: offside only counts where #9 Ibrahim Nwarafor is when the ball arrives | B (right): No: #9 Ibrahim Nwarafor is level with or behind the second-last defender | C: Yes: #9 Ibrahim Nwarafor is past the second-last defender

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 14. Offside: was it offside, level 1, deferred, question (first try)

**Model**

> Play has stopped for a goal kick. Back at 01:46, Ludlow Ferrymen’s #10 Chinedu Trankwo passed to #9 Ibrahim Nwarafor. Was Ibrahim Nwarafor offside when the pass was played?

**Template**

> Play has stopped for a goal kick. Back at 01:46: #10 Chinedu Trankwo passed to #9 Ibrahim Nwarafor. Was #9 Ibrahim Nwarafor offside when the pass was played?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:46; player = #10 Chinedu Trankwo; attacker = #9 Ibrahim Nwarafor
> Outcome: margin_m = 2.6; beyond_or_behind = behind the second-last defender; offside_call = onside
> Options: A: No: offside only counts where #9 Ibrahim Nwarafor is when the ball arrives | B (right): No: #9 Ibrahim Nwarafor is level with or behind the second-last defender | C: Yes: #9 Ibrahim Nwarafor is past the second-last defender

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 15. Offside: flag or not, level 1, live, feedback after a wrong pick (first try)

**Model**

> Offside is judged when the pass is played, not when #9 Ibrahim Nwarafor receives it. #9 Ibrahim Nwarafor was 2.6 m behind the second-last defender when the pass was played, so the call was onside. That means No: #9 Ibrahim Nwarafor is level with or behind the second-last defender.
> Takeaway: Check where the attacker is when the ball is passed, and compare them with the ball and the second-last defender.
> Common mix-up: Offside is judged when the player receives the ball, not when the pass is played.

**Template**

> An attacker is offside if, when the pass is played, they are in the other team's half and nearer the goal than both the ball and the second-last defender. Level counts as onside. The answer was No: #9 Ibrahim Nwarafor is level with or behind the second-last defender. #9 Ibrahim Nwarafor was 2.6 m behind the second-last defender when the pass was played, so the call was onside.
> Takeaway: Tell whether an attacker is offside when the ball is played to them.
> Common mix-up: Offside is judged when the player receives the ball, not when the pass is played.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:46; player = #10 Chinedu Trankwo; attacker = #9 Ibrahim Nwarafor
> Outcome: margin_m = 2.6; beyond_or_behind = behind the second-last defender; offside_call = onside
> Options: A: No: offside only counts where #9 Ibrahim Nwarafor is when the ball arrives | B (right): No: #9 Ibrahim Nwarafor is level with or behind the second-last defender | C: Yes: #9 Ibrahim Nwarafor is past the second-last defender

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 16. Offside: was it offside, level 1, deferred, feedback after a wrong pick (first try)

**Model**

> Offside is judged when the pass is played. At 01:46, #9 Ibrahim Nwarafor was 2.6 m behind the second-last defender when the pass was played, so the call was onside. That means it’s No: #9 Ibrahim Nwarafor is level with or behind the second-last defender, not the idea that you only check where he is when the ball arrives.
> Takeaway: Check where the attacker is when the pass is played, comparing them with the ball and the second-last defender.
> Common mix-up: Offside is judged when the player receives the ball, not when the pass is played.

**Template**

> An attacker is offside if, when the pass is played, they are in the other team's half and nearer the goal than both the ball and the second-last defender. Level counts as onside. The answer was No: #9 Ibrahim Nwarafor is level with or behind the second-last defender. #9 Ibrahim Nwarafor was 2.6 m behind the second-last defender when the pass was played, so the call was onside.
> Takeaway: Tell whether an attacker is offside when the ball is played to them.
> Common mix-up: Being in an offside position is always an offence.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Ludlow Ferrymen; opponent = Hexham Anchors; score = 0–0; minute = 01:46; player = #10 Chinedu Trankwo; attacker = #9 Ibrahim Nwarafor
> Outcome: margin_m = 2.6; beyond_or_behind = behind the second-last defender; offside_call = onside
> Options: A: No: offside only counts where #9 Ibrahim Nwarafor is when the ball arrives | B (right): No: #9 Ibrahim Nwarafor is level with or behind the second-last defender | C: Yes: #9 Ibrahim Nwarafor is past the second-last defender

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 17. Fouls and cards: after the foul, level 1, live, question (first try)

**Model**

> At 03:18, #14 Jamie Thornock commits a foul on a Ludlow Ferrymen player. Play is paused in transition. What happens next for the game?

**Template**

> #14 Jamie Thornock has fouled a Ludlow Ferrymen player. What happens now?

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Hexham Anchors; opponent = Ludlow Ferrymen; score = 0–1; minute = 03:18; fouler = #14 Jamie Thornock; fouled_team = Ludlow Ferrymen
> Outcome: restart_type = free kick; box_position = 12.5 m outside the penalty area; foul_outcome = Ludlow Ferrymen get a free kick.; booking_note = There was no booking.
> Options: A: Free kick to Hexham Anchors | B (right): Free kick to Ludlow Ferrymen | C: Penalty to Ludlow Ferrymen

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 18. Fouls and cards: why play on, level 3, live, question (first try)

**Model**

> At 08:16, #10 Emeka Ekegbe fouled a Bakewell Badgers player, but the referee allowed play to continue at 08:16 in the transition. With it still 0–0, why did they choose to play on rather than stop?

**Template**

> #10 Emeka Ekegbe fouled a Bakewell Badgers player, but the referee let play go on. Why?

<details><summary>Facts</summary>

> Before answering: home_team = Truro Otters; away_team = Bakewell Badgers; team = Truro Otters; opponent = Bakewell Badgers; score = 0–0; minute = 08:16; fouler = #10 Emeka Ekegbe; fouled_team = Bakewell Badgers
> Outcome: restart_type = advantage; box_position = 46.7 m outside the penalty area; foul_outcome = The referee let play go on, because Bakewell Badgers kept the ball.; booking_note = There was no booking.
> Options: A (right): Bakewell Badgers kept the ball, so stopping play would have helped Truro Otters | B: The referee didn't see the foul | C: A foul in the middle of the pitch isn't punished

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Gives nothing away before answering
- [ ] Reads naturally
- Notes:

### 19. Fouls and cards: after the foul, level 1, live, feedback after a right pick (repaired)

**Model**

> After the foul, play restarts with Free kick to Ludlow Ferrymen. Ludlow Ferrymen get a free kick. The restart is free kick for Ludlow Ferrymen from 12.5 m outside the penalty area. There was no booking. If Ludlow Ferrymen still have the ball and a chance, the referee can play advantage instead of stopping.
> Takeaway: After a foul you give the fouled team the restart, book only if there is a caution, and use advantage when play can continue.

**Template**

> After a foul, the team that was fouled gets a free kick where it happened, or a penalty if it was inside the fouling team's own penalty area. If the fouled team still has the ball and a chance, the referee can let play go on instead: that's advantage. The answer was Free kick to Ludlow Ferrymen. Ludlow Ferrymen get a free kick. There was no booking.
> Takeaway: Say what a foul gives, and to whom, why a player is booked, and when the referee plays advantage.

<details><summary>Facts</summary>

> Before answering: home_team = Hexham Anchors; away_team = Ludlow Ferrymen; team = Hexham Anchors; opponent = Ludlow Ferrymen; score = 0–1; minute = 03:18; fouler = #14 Jamie Thornock; fouled_team = Ludlow Ferrymen
> Outcome: restart_type = free kick; box_position = 12.5 m outside the penalty area; foul_outcome = Ludlow Ferrymen get a free kick.; booking_note = There was no booking.
> Options: A: Free kick to Hexham Anchors | B (right): Free kick to Ludlow Ferrymen | C: Penalty to Ludlow Ferrymen

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:

### 20. Fouls and cards: why play on, level 3, live, feedback after a right pick (first try)

**Model**

> Contact was 46.7 m outside the penalty area, so the restart hinged on what the referee saw. The referee let play go on, because Bakewell Badgers kept the ball. There was no booking. That is why play is allowed to continue when Bakewell Badgers kept the ball, so stopping play would have helped Truro Otters.
> Takeaway: Focus on what the foul gives and who it benefits, and on how the referee chooses advantage versus stopping play.

**Template**

> Where the contact happens decides the restart, not where the player lands: this foul was 46.7 m outside the penalty area. The referee let play go on, because Bakewell Badgers kept the ball. There was no booking. The answer was Bakewell Badgers kept the ball, so stopping play would have helped Truro Otters.
> Takeaway: Say what a foul gives, and to whom, why a player is booked, and when the referee plays advantage.

<details><summary>Facts</summary>

> Before answering: home_team = Truro Otters; away_team = Bakewell Badgers; team = Truro Otters; opponent = Bakewell Badgers; score = 0–0; minute = 08:16; fouler = #10 Emeka Ekegbe; fouled_team = Bakewell Badgers
> Outcome: restart_type = advantage; box_position = 46.7 m outside the penalty area; foul_outcome = The referee let play go on, because Bakewell Badgers kept the ball.; booking_note = There was no booking.
> Options: A (right): Bakewell Badgers kept the ball, so stopping play would have helped Truro Otters | B: The referee didn't see the foul | C: A foul in the middle of the pitch isn't punished

</details>

- [ ] True to the evidence
- [ ] Right for the level
- [ ] Reads naturally
- Notes:
