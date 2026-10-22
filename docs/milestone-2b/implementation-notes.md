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
