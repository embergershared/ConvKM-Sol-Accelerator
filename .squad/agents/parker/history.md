# Parker — History

## Project Context

- **Project:** ConvKM-Sol-Accelerator
- **Tech stack:** Python FastAPI backend (`src/api/`), React + TypeScript + Fluent UI v9 frontend (`src/App/`), Azure AI Foundry agents (`azure-ai-projects` SDK), Azure infra via azd/Bicep
- **User:** Emmanuel
- **Created:** 2026-06-01

## Learnings

### 2026-06-01 — Backend review of plans/agent-admin-ui.md

**SDK surface (azure-ai-projects==2.0.0b3 / azure-ai-agents==1.2.0b5):**
- `project_client.deployments` exists and `DeploymentsOperations.list()` is confirmed present, returns `ModelDeployment` objects with `name`, `model_name`, `model_version`, `model_publisher`, `capabilities`, `sku`. Filter by `type == "ModelDeployment"`.
- `project_client.agents` is a lazy-init property returning an `azure.ai.agents.aio.AgentsClient`. `create_version` is called in `01_create_agents.py` so must exist in 1.2.0b5, but `list_versions` and `get_version` are not verified anywhere in the codebase.
- `PromptAgentDefinition`, `FunctionTool`, `AzureAISearchAgentTool` are imported from `azure.ai.projects.models` (not `azure.ai.agents.models`). Unverifiable from az-cli SDK (1.1.0).
- The `Agent` model has a `metadata: Dict[str, str]` field (max 16 key/value pairs) — publisher attribution plan is feasible.

**Cache reality:**
- `thread_cache` is a module-level global in `chat_service.py` mapping `conversation_id -> thread_conversation_id`.
- There is no agent-object cache in ChatService. The agent is resolved fresh each call via `provider.get_agent(name=..., tools=...)`.
- `invalidate_agent_cache()` must call `self.get_thread_cache().clear()` which mutates the same module-level global — this works within one process.
- Thread-to-agent-version binding at Foundry is unverified. If Foundry threads survive cross-version, clearing may be unnecessary but harmless.

**Auth:**
- `auth_utils.get_authenticated_user_details` trusts `x-ms-client-principal-name` directly from headers with no cryptographic verification. Easy Auth sets these upstream; without Easy Auth, any caller can spoof them.
- `x-ms-client-principal` is a base64-decoded JSON (no signature check in `get_tenantid()`).

**sys.path in 01_create_agents.py:**
- Line 14 adds `infra/scripts/` to sys.path, NOT `src/api/`. Importing `agent_definition.py` from `src/api/services/` would require an additional path append. Better to make `agent_definition.py` a standalone plain module with no `Config` import, accepting connection params as function args.

**Test mocking pattern:**
- Standard pattern: `@patch("services.X.AIProjectClient")`, return `MagicMock` with `__aenter__`/`__aexit__` as `AsyncMock`.
- Admin service will need paginated async iterables mocked (e.g. `list_versions`, `deployments.list`). These require `AsyncMock` returning an `AsyncIterator`, not a plain `MagicMock`.

### 2026-06-01 — SDK Spike: agent version methods confirmed (azure-ai-projects==2.0.0b3)

**Critical clarification — two AgentsOperations classes exist, only one has versions:**
- `azure.ai.agents.aio.AgentsClient` → `azure.ai.agents.aio.operations._AgentsClientOperationsMixin` — ONLY has `create_agent`, `get_agent`, `list_agents`, `update_agent`, `delete_agent`. NO version management.
- `azure.ai.projects.aio.AIProjectClient.agents` → `azure.ai.projects.aio.operations.AgentsOperations` — has full version management. This is the correct client.

**All four target methods confirmed present in `azure.ai.projects.aio.operations.AgentsOperations`:**
- `create_version(agent_name, *, definition, metadata, description)` → `AgentVersionDetails`
- `list_versions(agent_name, *, limit, order, before)` → `AsyncItemPaged[AgentVersionDetails]`
- `get_version(agent_name, agent_version)` → `AgentVersionDetails`
- `update(agent_name, *, definition, metadata, description)` → `AgentDetails` (creates new immutable version, updates "latest" pointer)

**AgentVersionDetails fields:** `id`, `name`, `version`, `description`, `created_at`, `metadata`, `definition`, `object`

**AgentDetails fields:** `id`, `name`, `versions` (type `AgentObjectVersions` with `.latest: AgentVersionDetails`), `object`

**No `rollback` method exists.** Workaround: `get_version(name, old_id)` to retrieve old `definition`, then `update(name, definition=old_def)` — this promotes the old definition as the new latest.

**`deployments.list()`** is on `azure.ai.projects.aio.operations.DeploymentsOperations`. Returns `AsyncItemPaged[Deployment]`. The `ModelDeployment` discriminated subtype has: `name`, `model_name`, `model_version`, `model_publisher`, `capabilities`, `sku`, `connection_name`.

**All plan endpoints are feasible with current SDK.** Rollback requires a two-step `get_version` + `update` pattern, not a single call.

### 2026-06-01 — Plan review completed; v2 at plans/agent-admin-ui-v2.md; SDK confirmed via projects.AIProjectClient.agents (NOT agents.AgentsClient)

- Plan review session spawned ripley, parker, lambert, hicks for feedback, parker-1 for SDK spike, ripley-1 for v2 plan production.
- SDK spike confirmed all methods exist; critical discovery: version management on `AIProjectClient.agents` (azure.ai.projects), NOT `AgentsClient` (azure.ai.agents).
- Backend design review approved with changes: 4 blockers (SDK now resolved, import path, cache semantics, concurrency) and design recommendations (PUT vs POST, idempotency, auth caveat).
- v1 scope instructions-only (no model picker, no version history); v2 scopes on SDK (now resolved).
- 6 decisions merged; 6 orchestration logs; session log created.
- Implementation ready on v1 scope immediately.
