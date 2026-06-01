# Ripley — History

## Project Context

- **Project:** ConvKM-Sol-Accelerator
- **Tech stack:** Python FastAPI backend (`src/api/`), React + TypeScript + Fluent UI v9 frontend (`src/App/`), Azure AI Foundry agents (`azure-ai-projects` SDK), Azure infra via azd/Bicep
- **User:** Emmanuel
- **Created:** 2026-06-01

## Learnings

### 2026-06-01 — Review of plans/agent-admin-ui.md

- **SDK surface unverified**: `azure-ai-projects==2.0.0b3` is installed. Only `agents.create_version` is actually used in the codebase. No evidence of `list_versions`, `get_version`, or `deployments.list()` anywhere — these are speculative API calls. Beta SDKs routinely break between releases.
- **Auth gap is a real security issue**: `x-ms-client-principal-name` is only set by App Service EasyAuth. Without EasyAuth enabled, the header is trivially forgeable by any HTTP client. The plan's "no auth gate" stance leaves a production-reachable endpoint that can change system prompts, swap models, and exfiltrate data.
- **Cache invalidation is process-local only**: The App Service can scale to N instances. The `thread_cache` (ExpCache) and any "invalidate" signal only hit the process handling the admin POST. Other instances see stale agent definitions until their own cache TTL expires (up to 3600s for thread_cache).
- **Tools coupling risk**: If `agent_definition.py` is shared but one consumer drifts (e.g., search index name changes in infra but only the script arg is updated), the parity test only catches this if it tests the *resolved values* at runtime, not just structural shape.
- **No concurrency control**: Two admins publishing simultaneously = last-write-wins with no conflict detection. Foundry append-only model means both versions exist but "active" is ambiguous without an explicit pointer.
- **Verdict**: REJECT — must address SDK verification, auth minimum bar, and cache invalidation scope before implementation begins.

### 2026-06-01 — v2 plan produced (plans/agent-admin-ui-v2.md)

- **Scope cut worked:** Dropping model picker and version history from v1 removes the SDK uncertainty from the critical path. v1 is instructions-only edit with auth gate — shippable regardless of spike outcome.
- **Conditional sections are the right pattern:** Marking `[IF SDK has list_versions]` / `[IF SDK lacks list_versions]` keeps the plan concrete without blocking on Parker's spike. Implementers know exactly what to do in each case.
- **Concurrency via expected_version_id:** OCC with 409 is the simplest reversible concurrency control — no distributed locks, no saga. Race condition is now explicit and handled.
- **Cache honesty matters:** Documenting 3600s worst-case in both the plan and the UI copy prevents support confusion later. No hand-waving about "a few seconds."
- **First frontend test:** RTL test infrastructure (setupTests.ts global.fetch mock) is a project-first — call it out so reviewers don't trip over the bootstrapping.

### 2026-06-01 — Plan review completed; v2 at plans/agent-admin-ui-v2.md; SDK confirmed via projects.AIProjectClient.agents (NOT agents.AgentsClient)

- Plan review session spawned ripley, parker, lambert, hicks for feedback, parker-1 for SDK spike, ripley-1 for v2 plan production.
- All agents approved/confirmed: SDK methods exist (`create_version`, `list_versions`, `get_version`, `deployments.list`); critical client-selection discovery (use `AIProjectClient.agents`, not `AgentsClient`); auth gate mandatory; concurrency control via `expected_version_id`; cache TTL 3600s explicit.
- v1 scope cut to instructions-only edit (no model picker, no version history); v2 scope gates on SDK spike (now resolved).
- 6 decisions merged into `.squad/decisions.md`; 6 orchestration logs written; session log created.
- Next: implementation ready on v1 scope immediately.
- 2026-06-01T20:19:51Z: Published agent-admin-ui-v2.md v2.1 — collapsed SDK conditionals (Parker spike RESOLVED), added critical wrong-client warning (AIProjectClient vs AgentsClient).

### 2026-06-01 — v1 Reviewer Gate: APPROVE WITH NITS

- **Verdict:** APPROVE WITH NITS — all 7 acceptance criteria pass, all plan-required guarantees met with evidence, 38 new tests (zero regressions).
- **Implementation quality:** Clean separation (pure function module, service wrapper, route layer, auth dependency). Correct SDK client used. Cache invalidation targets module-global correctly despite per-request ChatService() instantiation.
- **Lambert's 3 deviations all justified:** isAdminPanelOpen (overlay doesn't participate in column math), raw fetch (401 interceptor would preempt per-status handling), Fluent ESM→CJS mapper (jsdom limitation).
- **Nits (non-blocking):** unused `asynccontextmanager` import in admin_routes.py; per-request ChatService() instantiation deserves a comment; parity test count docstring says 9 but there are 10 tests.
- **Key architectural insight:** The module-global `thread_cache` pattern in `chat_service.py` means any ChatService() instance accesses the same cache — but this is non-obvious and fragile if someone refactors to instance-level caches later.
- **v2 debt accepted:** process-local cache/idempotency, no rate limiting, non-blocking secret scan, no persistent audit log, overlay UI will outgrow single page.

### 2026-06-01 — v1 Implementation Complete — All Metrics Green

- **Verdict:** v1 implementation of agent-admin-ui shipped — Reviewer APPROVE WITH NITS.
- **Agents dispatched:** parker-2, lambert-1, hicks-1, hicks-2, ripley-3, lambert-2 (6 total).
- **Files created:** 11 (4 backend services, 4 backend tests, 3 frontend + types).
- **Files modified:** 6 (app.py, admin_routes, conftest, App.tsx, setupTests.ts, package.json, LocalDevelopmentSetup.md).
- **Test results:** 196 backend + 11 frontend passing, zero failing, zero pre-existing regressions.
- **Acceptance criteria:** 7/7 pass with concrete evidence.
- **Plan guarantees:** 17/17 verified locked in.
- **Surface assumptions:** 10/10 locked by test suite.
- **Handoff:** Ready to merge; nits are polish-only post-merge tasks.
