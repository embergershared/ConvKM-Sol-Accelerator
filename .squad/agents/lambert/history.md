# Lambert — History

## Project Context

- **Project:** ConvKM-Sol-Accelerator
- **Tech stack:** Python FastAPI backend (`src/api/`), React + TypeScript + Fluent UI v9 frontend (`src/App/`), Azure AI Foundry agents (`azure-ai-projects` SDK), Azure infra via azd/Bicep
- **User:** Emmanuel
- **Created:** 2026-06-01

## Learnings

### 2026-06-07T00:57:20.783+00:00 — Chat model dropdown completed

**Status:** Shipped + Orchestration logged

- Model selector Dropdown added to `Chat.tsx` header using Fluent UI v9 with state in `appSlice`
- Selection persists across `startNewConversation()`; fallback to `is_default: true` model or first model if selection no longer available
- `useChatApi` forwards selected model on chat and follow-up requests
- Frontend build + 12 tests passed
- Decision entry merged to squad/decisions.md
- **Files:** Chat.tsx, appSlice.ts, useChatApi.ts, api.ts, Chat.css, AppTypes.ts
- Prerequisite: backend `GET /api/models` returns `{id, display_name, is_default}` shape (implemented upstream)

### 2026-06-07T00:57:20.783+00:00 — Chat model selector shipped

- Added a Foundry model picker to `Chat.tsx` using Fluent UI v9 `Dropdown` + `Option`, with state stored in `appSlice` so the selection survives `startNewConversation()`.
- `appSlice.fetchModels` now hydrates `availableModels` from `GET /api/models` and preserves any still-valid selection; otherwise it falls back to the API model marked `is_default: true` (or the first returned model).
- `useChatApi` now forwards the selected `model` on both normal chat requests and automatic chart follow-up requests so the whole conversation flow stays on the chosen deployment.

### 2026-06-01 — Frontend review of `plans/agent-admin-ui.md`

- **No router in this project.** `package.json` has no `react-router-dom`. The existing navigation pattern in `App.tsx` is a `panelShowStates` boolean map. A hash route requires manual `window.location.hash` listening — zero framework support. The plan's preference for `#/admin` conflicts with established convention; a simple `showAdmin: boolean` state fits the codebase perfectly.
- **Both Fluent v8 AND v9 are present.** `@fluentui/react` (v8) is used in `ChatHistoryPanel.tsx` and `Chat.tsx` (Spinner, DefaultButton). `@fluentui/react-components` (v9) is also installed. New components should use v9 only, but the plan must be explicit — the project has a mixed inheritance.
- **RTL + jest confirmed.** `@testing-library/react` ^16, `@testing-library/jest-dom` ^6, `@testing-library/user-event` ^14, `@types/jest` ^30 are all in `package.json`.
- **The existing Dialog pattern uses Fluent v8** (`@fluentui/react` `Dialog`) in `ChatHistoryPanel.tsx`. New admin dialogs should use v9 `Dialog` from `@fluentui/react-components` for consistency with new component direction, but this is a choice to document.
- **State management via Redux** (`@reduxjs/toolkit`, `react-redux`). The plan proposes local `useState` for admin — acceptable for a standalone panel but worth noting the project uses Redux slices for shared state.
- **No ETag / version-id conflict detection in the plan.** The backend has no `version_id` on GET /api/admin/agent in the current plan. Must add it before the frontend can guard against stale-state races.
- **Plan verdict: APPROVE WITH CHANGES** — 3 must-fix items, several design clarifications needed before implementation.

### 2026-06-01 — Plan review completed; v2 at plans/agent-admin-ui-v2.md; SDK confirmed via projects.AIProjectClient.agents (NOT agents.AgentsClient)

- Plan review session with ripley, parker, hicks for feedback; parker-1 SDK spike; ripley-1 v2 plan.
- Frontend design review approved with changes: 3 must-fix blockers (routing pattern, gear visibility, stale-state ETag) and 4 design improvements (Combobox validation, textarea guards, confirm flow, rollback preview, pagination).
- All frontend items addressed in v2 plan with panelShowStates pattern, Fluent v9, no react-router-dom.
- v1 scope instructions-only; v2 scope gates on SDK (now confirmed).
- 6 decisions merged; orchestration/session logs created.
- Implementation ready on v1 scope.

### 2026-06-01 — v1 Frontend implementation shipped

- **Files created:** `src/App/src/types/AgentAdmin.ts`, `src/App/src/api/adminApi.ts`, `src/App/src/components/Admin/AgentAdmin.tsx`, `src/App/src/components/Admin/AgentAdmin.test.tsx`.
- **Files modified:** `src/App/src/App.tsx` (ADMIN panel, gear icon, focus management), `src/App/src/setupTests.ts` (fetch mock + ResizeObserver mock), `src/App/package.json` (Jest moduleNameMapper for Fluent v9 ESM).
- **Panel approach:** Used a separate `isAdminPanelOpen` boolean state in App.tsx instead of adding ADMIN to `panelShowStates`. This avoids the column-width layout calculation counting the admin overlay as an open panel. `ADMIN: "ADMIN"` was added to the `panels` const for naming only.
- **Unsaved-changes prompt:** Fluent v9 `Dialog` shown when `handleClose` is called with `hasUnsavedChanges === true`. `beforeunload` event listener also attached while there are unsaved changes.
- **adminApi.ts uses raw `fetch`** (not httpClient) because httpClient's 401 interceptor throws before we can inspect the status — we need per-status control for all error paths.
- **Jest fix required:** `@fluentui/react-icons/lib/providers.js` is ESM and is required transitively by `@fluentui/react-provider` (CJS). Added `moduleNameMapper` in package.json to redirect to the CJS build at `lib-cjs/`. Also mocked `ResizeObserver` in setupTests.ts — jsdom omits it but Fluent v9 MessageBar references it.
- **All 11 RTL tests pass.** Baseline App.test.tsx also passes unchanged.

### 2026-06-01 — Updated LocalDevelopmentSetup.md with Agent Admin Panel section

- Added `## Agent Admin Panel` section to documents/LocalDevelopmentSetup.md before Troubleshooting; covers feature overview, visibility toggle (REACT_APP_SHOW_ADMIN env var + ?admin=1 query param), authentication (x-ms-client-principal-id header + ADMIN_AUTH_BYPASS bypass), 60-minute cache propagation caveat, required env vars (AZURE_AI_AGENT_ENDPOINT, AGENT_NAME_CONVERSATION), and v2 feature roadmap (model picker, version history, rollback, diff preview).

### 2026-06-01 — v1 Implementation Complete — Reviewer APPROVE WITH NITS

- **Ripley's verdict:** APPROVE WITH NITS — all 7 acceptance criteria pass; all plan-required guarantees met; 196 backend + 11 frontend tests green (zero regressions).
- **Team composition:** parker-2 backend + lambert-1 frontend + hicks-1 tests (initial) + hicks-2 tests (reconciliation) + ripley-3 review + lambert-2 docs.
- **Key achievements:** Correct SDK client (AIProjectClient.agents, not AgentsClient); concurrency control via expected_version_id + 409; thread cache invalidation; auth gate (x-ms-client-principal-id required); 9 parity invariants locked by tests; process-local cache/idempotency documented with v2 debt.
- **Nits (polish-only):** Remove unused asynccontextmanager import; add ChatService comment; update parity docstring count.
