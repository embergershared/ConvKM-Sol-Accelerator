# Lambert — History

## Project Context

- **Project:** ConvKM-Sol-Accelerator
- **Tech stack:** Python FastAPI backend (`src/api/`), React + TypeScript + Fluent UI v9 frontend (`src/App/`), Azure AI Foundry agents (`azure-ai-projects` SDK), Azure infra via azd/Bicep
- **User:** Emmanuel
- **Created:** 2026-06-01

## Learnings

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
