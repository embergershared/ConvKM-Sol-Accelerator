# Admin UI: edit Conversation Agent instructions & model

## Problem
The `KM-ConversationAgent` is provisioned by `infra/scripts/agent_scripts/01_create_agents.py` with hard-coded `conversation_agent_instruction` and a single `gptModelName`. Changing either today requires editing the script and re-running `run_create_agents_scripts.sh` (or `azd provision`). We want an in-app admin page that lets a signed-in user:

- View the current active instructions + model
- Edit instructions in a text area
- Pick a different model deployment (free-text with autocomplete validated against the AI Foundry project's deployments)
- Publish a new agent version live
- See version history (timestamp + publisher) and roll back to a previous version

Scope is **only** `KM-ConversationAgent`. Title and topic-mining agents are out of scope.

## Approach

### Runtime model
At runtime the API resolves the agent by `AGENT_NAME_CONVERSATION` (`src/api/common/config/config.py:44`) and `provider.get_agent(name=...)` (`chat_service.py:154`). The bound model and instructions live in the Foundry agent **version**. So "publish" = call `project_client.agents.create_version(agent_name=<same>, definition=PromptAgentDefinition(model=..., instructions=..., tools=<same as 01_create_agents.py>))`. This automatically produces a new version, preserves the agent name, and the API picks it up on the next `get_agent` call (cache TTL noted below).

### Backend (FastAPI)
New router `src/api/api/admin_routes.py` mounted at `/api/admin` (no auth gate for now — internal demo). Endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/admin/agent` | Return current active version: name, model, instructions, version id, created_at, created_by |
| `GET`  | `/api/admin/agent/versions` | List recent versions (id, model, created_at, created_by, is_active) |
| `GET`  | `/api/admin/agent/versions/{version_id}` | Return full instructions + model for a specific version (for rollback preview) |
| `POST` | `/api/admin/agent` | Body: `{ instructions: str, model: str }`. Creates a new version using the same tools as `01_create_agents.py`. Records publisher from `x-ms-client-principal-name` (or `sample_user` locally). Returns new active version. |
| `POST` | `/api/admin/agent/rollback` | Body: `{ version_id: str }`. Re-publishes a new version cloning the target's instructions+model (Foundry agents are append-only; "rollback" = publish-as-new). |
| `GET`  | `/api/admin/models` | List model deployments available in the AI Foundry project (used by the model picker autocomplete) |

Implementation notes:
- New service `src/api/services/agent_admin_service.py` wraps `AIProjectClient` and `azure-ai-projects` agent version APIs. Reuses `get_azure_credential_async` from `helpers/azure_credential_utils.py` and `Config().ai_project_endpoint`.
- The tools definition (`get_sql_response` FunctionTool + `AzureAISearchAgentTool`) must be **factored out** of `infra/scripts/agent_scripts/01_create_agents.py` into a shared module (e.g. `src/api/services/agent_definition.py`) and **imported by both** the create-agents script and the new service so behavior stays in sync. Acceptance: `01_create_agents.py` continues to work unchanged in behavior.
- Publisher attribution: read `x-ms-client-principal-name` via existing `get_authenticated_user_details(request.headers)`; fall back to `"local-dev"`. Store in version `metadata` dict (Foundry agent versions support a metadata bag) so we can show "who published" without a separate database.
- Model listing: call Azure AI Foundry project's deployments API (`project_client.deployments.list()` if available in the installed `azure-ai-projects` SDK; otherwise hit the underlying Cognitive Services account via management SDK using `Config().ai_project_endpoint`'s parent resource). Cache for 60s.
- After a successful publish, **invalidate the in-process agent thread cache** in `ChatService` so existing conversations pick up the new version on the next turn. Add a small `invalidate_agent_cache()` helper on `ChatService` and call it from the admin route. (Document the caveat that an in-flight stream finishes on the old version.)

### Frontend (React)
- New route/panel `Admin` in `src/App/src/components/Admin/AgentAdmin.tsx` accessible via a gear icon in the existing header (`App.tsx` around the `AppLogo` row). No route library is currently in use — add a simple panel toggle in `App.tsx` state alongside the existing `panels` map, OR introduce a hash-based route `#/admin`. Prefer the hash route to avoid cluttering the main layout state.
- Use Fluent UI v9 components already in the project (`Textarea`, `Combobox`, `Button`, `MessageBar`, `Spinner`, `Dialog` for rollback confirm).
- Components:
  - `AgentAdmin.tsx` — main page: shows current model + instructions, edit form, Publish button, version history table with Rollback action
  - API client helpers added to `src/App/src/api/api.ts`: `getAgent`, `listAgentVersions`, `getAgentVersion`, `publishAgent`, `rollbackAgent`, `listModels`
  - Types in `src/App/src/types/AgentAdmin.ts`
- UX details:
  - Model picker = Fluent `Combobox` with `freeform` enabled, options from `/api/admin/models`, client-side validation that selection is non-empty
  - Instructions = `Textarea` with monospace font, char counter, unsaved-changes warning
  - Publish button disabled if neither instructions nor model changed
  - Toast on success showing new version id; error MessageBar on failure
  - Version history table columns: Version, Model, Published at, Published by, Active, Actions (Rollback)
  - Rollback confirmation dialog explains it publishes a new version cloning the selected one (Foundry versions are immutable/append-only)

### Tests
- Backend: add `src/tests/api/services/test_agent_admin_service.py` and `src/tests/api/api/test_admin_routes.py` mocking `AIProjectClient` (mirror style of existing `test_chat_service.py`). Cover: get current, publish (verifies tools wiring matches `01_create_agents.py`), rollback, list models, list versions.
- Backend: refactor test for `01_create_agents.py` if one exists, or add a smoke test that imports the shared `agent_definition.py` and verifies tool names/params are unchanged.
- Frontend: add `AgentAdmin.test.tsx` using the existing RTL + jest setup — render the page with mocked fetch responses, verify publish flow and rollback dialog.
- Run baselines first: `pytest` in `src/tests`, `npm test -- --watchAll=false` in `src/App`.

### Docs
- Add a short section to `documents/LocalDevelopmentSetup.md` describing the `/admin` page and the env vars it needs (none new — reuses `AZURE_AI_AGENT_ENDPOINT`, `AGENT_NAME_CONVERSATION`).
- Note in the new section that the page is **unauthenticated** and intended for internal/demo use; future work item: gate via Easy Auth admin list.

## Out of scope (explicitly)
- Auth/authorization on the admin page (deferred; noted in docs)
- Editing the Title agent or the data-processing topic agents
- Editing the agent's tool set (only model + instructions)
- Deploying new model deployments from the UI (must already exist in the Foundry project)
- Persistent audit log beyond what Foundry version metadata stores

## Risks / decisions made
- **Foundry versioning semantics**: assumes `azure-ai-projects` supports `agents.create_version` + listing versions + reading a specific version. The create script already uses `create_version`; we'll verify list/get APIs during implementation and adjust (worst case: store version pointer + history in our own SQL table).
- **Rollback is publish-as-new** rather than mutating "active version" pointer — simplest and matches Foundry's append-only model.
- **Tools coupling**: shared `agent_definition.py` is the single source of truth. If `01_create_agents.py` and the service drift, the next publish would silently change tool wiring — the shared module + tests guard against this.
- **Cache invalidation** clears only the local process's thread cache; in a multi-instance App Service deployment, other instances continue serving the previous version until their own next `get_agent` call (the provider does not cache long-term, but document the few-second propagation window).

## Todos
Tracked in SQL `todos` table (see initial inserts below).
