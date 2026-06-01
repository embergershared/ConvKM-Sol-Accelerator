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
