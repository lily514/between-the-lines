# Milestone 2b: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## 0 — Plan and CLAUDE.md (2026-10-22)
**Plan said:** CLAUDE.md's new rule is "No viewer id or name goes in a prompt", and the plan names Lily's Azure tenant, endpoint and subscription.
**We did:** the rule says "No viewer id, name or club", as the plan's own Decisions section says. The repo went public on 2026-10-22, so the committed plan uses placeholders (`<tenant-id>`, `<resource-name>`, …) for Lily's Azure details, at her request.
**Why:** the club is about the viewer too; the real values belong in Lily's environment, not on GitHub.
**Affects:** `docs/setup.md` (T1) uses the same placeholders.

## T1 — Azure setup and client (2026-10-22)
**Plan said:** a setup section with the steps Lily ran; `ModelClient` and `AzureClient` (`AzureCliCredential(tenant_id)`, reasoning effort `none`); the dependencies; `btl tutor-ping`; a request-shape test with a mock transport.
**We did:** as planned, with these choices:
- **The openai SDK (version 3) sends through `httpx2`,** the fork Starlette already uses here, not `httpx`. The mock transport is `httpx2.MockTransport`.
- **`AzureClient` takes a `credential`,** by default `AzureCliCredential(tenant_id=…)` for the settings' tenant. Tests pass a fake one that records the token scope, so the bearer token is checked without `az`. A separate test checks the CLI credential is scoped to the named tenant.
- **No SDK retries** (`max_retries=0`): the Tutor's own time budget and template fallback (T4) decide what happens after a failure.
- **Every failure becomes a `ModelError`:** a refused or rate-limited call, a server error, a timeout, an incomplete reply, and a failed sign-in (before anything is sent).
- **`FakeClient` arrives now,** for T2–T6. `ReplayClient` comes with T7, which records the replies it plays back.
- **A test keeps the network in one place:** in the whole `btl` package, only `tutor/azure.py` imports `openai`, `azure` or `httpx2`.
- **Setup:** `docs/setup.md` gets "Optional: the AI Tutor (Azure)", with placeholders for Lily's values. The steps are written as `az` commands equivalent to what Lily set up. The object id comes from the token's `oid` claim, decoded with Python, because plain `base64 -d` can fail on unpadded tokens.

**Checked against Azure:** `btl tutor-ping` with Lily's `az login` (her default tenant is a different one) reached `gpt-5.4-nano` in 2.54 s, with 50 tokens in and 12 out, and replied `{"reply":"ready"}`. The service reports the model as `gpt-5.4-nano`, without its version.
**Why:** the plan left these details open, and the SDK's HTTP library changed.
**Affects:** T7 adds `ReplayClient`. The `source` label will read `gpt-5.4-nano`, as the service names the model.

## T2 — Verifier (2026-10-22)
**Plan said:** every check in the table; a contract suite where each bad output is rejected for exactly its own reason; the template Tutor's wording passes over 40 seeds × every concept and kind of question × levels × right and wrong; `verifier.md`. If templates or map text fail a check, record it and let Lily decide, without loosening the check.
**We did:** as planned, with these choices and two decisions by Lily:
- **The templates failed `grounded` for ten of the twelve kinds of question.** Outside pass questions, the feedback ended "The answer was {answer}.", which cites no outcome fact. Lily chose to make the templates cite one, rather than exempt them. After "The answer was {answer}." comes the fact that settles it (`SETTLED_BY`): for a restart "It was a {restart_type} to {restart_team}.", for a counter-press "{player} won the ball back {seconds_to_regain} seconds after it was lost." It is added only when the level's explanation doesn't already cite an outcome, so in practice mostly at level 1.
- **The fouls takeaway was 27 words,** over the limit of 25. Lily chose to reword the concept map rather than raise the limit. "Say what a foul gives (a free kick or a penalty, and to whom), why a player is booked, and when the referee lets play go on." became "Say what a foul gives, and to whom, why a player is booked, and when the referee plays advantage."
- **Number words:** "one", "first", "last" and "once" aren't counted as numbers. In the templates and the map they are always a pronoun or an adverb ("this one broke…", "drop back first", "at once", "last touched"). A side's half ("the other team's half") is allowed along with the plan's phrases.
- **`hint` by label word** counts a word that is in some labels but not all, so "free kick", when two of three options are free kicks, still counts. Joining words ("to", "when") and words any football question uses ("ball", "back", "stopped", "referee") are left out. Otherwise the templates' own "Play has stopped… Back at…" and "lost the ball" were rejected. Words from the question's own subject ("offside" in "was it offside") don't count either.
- **`names`** skips a lone capital letter: "option B" is the `hint` check's business.
- **`comparison`** rejects a comparative it can't order ("better", "faster", or "than" without "more" or "fewer").
- **Results** are a `Check` of `Failure`s (check name and reason); `reasons` lists the failed checks' names for logs and repair. Feedback is checked as `FeedbackText(explanation, takeaway, misconception index)`.

**Learned:** rewording the map changes the fouls packs' ids, because a pack's id hashes its contents, and the common mix-up is picked by pack id. A fouls question can therefore offer a different mix-up than before. Saved records are unaffected: replay doesn't compare stored pack ids. A pending web answer from before an upgrade gets 409 and fetches the question again, as in 2c. The page's captured test payloads still show the old closing sentence; they test layout, not wording.
**Why:** the templates must pass the Verifier's own rules, and Lily decided both failures.
**Affects:** the terminal and the page now show the settling fact after "The answer was …". T4's fallback uses these templates.

## T3 — Prompts and FoundryTutor (2026-10-22)
**Plan said:** prompt builders and schemas; over 40 seeds and every kind of question, no question prompt holds an outcome fact's name, or a value the context doesn't also show, and no prompt holds the viewer id; a malformed reply raises `ModelError`.
**We did:** as planned, with these choices:
- **`question_request(view, plain)`** sends the view's own facts as `{slot} = value`, the option labels it must not point at, and the template's wording as "a plain version" of what is asked. **`feedback_request(pack, grade)`** sends:
  - the context, outcome and option facts, in separate lists;
  - `{answer}` and `{chosen}` spelled out;
  - the concept text at the viewer's level, and the objective;
  - the numbered mix-ups;
  - whether the pick was right.
- **A `Repair` (the first reply and its failures)** can be added to either request, ready for T4.
- **The leak test** allows an outcome value that the question view already shows anywhere: in a label ("One"), or in the question's own subject ("offside").
- **No viewer:** the builders take no argument that could carry the viewer, which a test pins.
- **`FoundryTutor.word_question` and `word_feedback`** return the parsed text with the reply (model, tokens, time) for T4's records. Non-JSON, a missing or empty field, or a misconception that isn't a whole number is a `ModelError`.

**Learned, from five live tries with `gpt-5.4-nano`** (one of each kind of question asked, before and after two rounds of prompt changes):
- **Questions passed the Verifier every time.** Feedback first failed every time: the model wrote values beside their slots, prefixed outcome facts with `answer.`, and left out `{answer}`. Telling it to write only the slot, spelling out `{answer}` and `{chosen}`, and marking whole-sentence facts brought it to two in five.
- **Two Verifier gaps, now closed:** braces that aren't a slot (`{second-last defender}`) passed `slots`; and text the checks accepted read badly once filled ("behind the second-last defender the second-last defender", "There was no booking, since There was no booking.."). A new **`echo`** check rejects words said twice in a row, a name or phrase written out beside its own slot, and a whole-sentence fact used inside another sentence. `names` now reads the filled text, since a value can end one sentence and the text start the next.
- **Accepted but wrong:** one question put the passer and the receiver in different clubs, and one feedback said play would "turn into 0–0 play". No check can catch these; they are what T7's hand review is for. The pass rate is far below T7's 80% target, so T7's prompt iteration matters.

**Why:** the plan left the prompts' wording open, and the live tries showed what the model gets wrong.
**Affects:** T4 (repairs use `Repair`, and `echo` is one of the reasons it can send). T7 (prompt iteration starts from `PROMPT_VERSION` 1). `verifier.md` now describes `echo`.

## T4 — VerifiedTutor and CachedTutor (2026-10-22)
**Plan said:** `VerifiedTutor(primary, fallback, on_check)`: the model's text if the Verifier passes it, one repair with the failed checks' reasons, then the template; `CALL_BUDGET` 12 s covering the repair; `source` labels; a `CheckRecord` per call. `CachedTutor` by pack, and by pack and pick, least recently used first.
**We did:** as planned, with these choices:
- **The repair gets only what is left of the budget,** and isn't tried with less than a second left (`MIN_REPAIR_SECONDS`). `FoundryTutor` now takes a per-call `timeout` for that. The clock is a parameter, so tests control it.
- **A question has no source field** (`TutorQuestion` is only text), so who worded a question shows only in the `CheckRecord`s. The page and terminal label feedback, as planned.
- **The fallback's source** lists the last try's failed checks ("template (fallback: slots, bare_number)"), or "no reply" when the call failed, timed out or wasn't the JSON asked for.
- **A `CheckRecord`** holds the prompt version, kind, pack id, attempt (1, or 2 for the repair), whether it passed, the failed checks, any error, and the model, time and tokens. Writing them to `data/tutor-log.jsonl` is T5's.

**Checked live** (one feedback after a wrong pick for each of six kinds of question, with `gpt-5.4-nano`):
- **Questions:** all six passed first time, in 1.4–2.5 s.
- **Feedback:** one passed first time, three passed after the repair, and two fell back to the template (one for `slots` and `bare_number`, one for `grounded`). Feedback took 2.1–4.2 s with the repair, well inside the budget.

**Why:** the plan left these details open.
**Affects:** T5 and T6 build the Tutor as `VerifiedTutor` (wrapped in `CachedTutor` on the server) and log its records.

## T5 — Terminal wiring (2026-10-22)
**Plan said:** `btl learn` and `btl demo-viewer --tutor template|foundry`, on the path 2e built; a spinner while waiting; the source line; the takeaway filled; `data/tutor-log.jsonl`; with the fake model, every shown text passes the Verifier, and the attempt log is identical to the template run's, with and without a club.
**We did:** as planned, with these choices:
- **`--tutor foundry`** builds `VerifiedTutor(FoundryTutor(AzureClient(…)), TemplateTutor(), log)`, wrapped in a `WaitingTutor` that shows "Wording the question…" or "Wording the feedback…" while it waits. Without the three `BTL_FOUNDRY_*` settings it stops and says which are missing.
- **`--tutor-log`** says where the records go (by default `data/tutor-log.jsonl`, under the gitignored `backend/data/`). Each line is a `CheckRecord` with a `logged_at` time from the CLI's clock, appended by `io.append_json_line`.
- **"Worded by …"** follows the takeaway, in dim text, for every Tutor ("Worded by template." by default).
- **The session fills the takeaway's slots,** the one change in `learn/`.
- **The fake model for end-to-end tests** (`tests/fixtures/tutor.py`) words every question the same way, and writes feedback from the first outcome fact in its prompt. Every third feedback, and its repair, gives a verdict instead, so the fallback is used too. A test checks the attempt log is identical with the template and with the fake model, with and without a club. It also checks both the model's words and the template's are shown, and no slot is left unfilled.

**Checked live:** `btl demo-viewer --seed 7 --tutor foundry` made the same picks and moved the bars exactly as the template run did.
- **Questions:** 15 of 18 passed first time and all 18 after the repair (the three failures were `bare_number`).
- **Feedback:** 7 of 18 passed first time and 6 more after the repair; 5 fell back to the template. The most common failures were `slots` (8), `echo` (5) and `grounded` (4).
- **Cost and speed:** 50 calls, median 1.7 s and 95th percentile 2.3 s, with about 44,000 tokens in and 4,600 out for three matches.

**Why:** the plan left these details open.
**Affects:** T6 reuses `ByKind`, and builds the server's Tutor the same way, wrapped in `CachedTutor`. T7's evaluation starts from these numbers.
