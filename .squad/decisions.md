# Squad Decisions

## 2026-06-01 Session: Agent Admin UI Plan Review

### Decision 1: Plans/agent-admin-ui.md — REJECTED (Ripley, 2026-06-01)
**Status:** Rejected — revision required before implementation

**Issue:** Three blocking items:
1. Unverified SDK surface (`list_versions`, `get_version`, `deployments.list()` not proven in `azure-ai-projects==2.0.0b3`)
2. No authentication on endpoint modifying system prompts and model bindings
3. Cache invalidation is process-local in potentially multi-instance deployment

**Required Actions:**
- Parker or implementer must spike SDK surface before committing to API design
- Add minimum auth gate (EasyAuth + allowed-principals list, or validate `x-ms-client-principal-id` presence)
- Document whether multi-instance staleness is accepted or requires fix (Redis pub/sub, polling, or Foundry webhook)

---

### Decision 2: SDK Spike Result — All Methods Confirmed (Parker, 2026-06-01)
**Status:** RESOLVED — Critical discovery documented

**Finding:** All required methods exist. Critical: version management lives in `azure.ai.projects.aio.operations.AgentsOperations` on `AIProjectClient`, NOT `azure.ai.agents.aio.AgentsClient`. Using wrong client silently fails.

**Installed versions:**
- azure-ai-projects: 2.0.0b3
- azure-ai-agents: 1.2.0b5

**Method status:**
- `agents.create_version` ✅ `azure.ai.projects.aio.operations.AgentsOperations`
- `agents.list_versions` ✅ `azure.ai.projects.aio.operations.AgentsOperations`
- `agents.get_version` ✅ `azure.ai.projects.aio.operations.AgentsOperations`
- `deployments.list()` ✅ `azure.ai.projects.aio.operations.DeploymentsOperations`

**Workaround for missing rollback method:**
```python
# 1. Fetch target version definition
old_version = await project_client.agents.get_version(agent_name, target_version_id)
# 2. Push as new update (creates immutable version, updates latest pointer)
await project_client.agents.update(agent_name, definition=old_version.definition)
```
Creates new version entry (acceptable for admin UI).

---

### Decision 3: Backend Design Review — Requires Changes (Parker, 2026-06-01)
**Status:** APPROVE WITH CHANGES

**Four blockers:**
1. **`list_versions` and `get_version` on `project_client.agents` are unverified** (now resolved by spike)
2. **`agent_definition.py` import conflict:** Can't import `Config` from `01_create_agents.py` path. Shared module must take `connection_name` and `index_name` as function arguments.
3. **`invalidate_agent_cache()` clears threads, not agent objects.** Must call `self.get_thread_cache().clear()` and document what is being cleared and why.
4. **Concurrent publishes produce two live versions with no winner.** Must add `current_version_id` field for race detection.

**Design recommendations:**
- POST → PUT for publish semantics (`PUT /api/admin/agent` for resource replacement)
- POST `/api/admin/agent/rollback` → POST `/api/admin/agent/versions/{version_id}/activate`
- Idempotency: add `X-Idempotency-Key` header support or pre-flight version check
- `deployments.list()` fallback to management SDK is unnecessary (confirmed present; filter by `type == "ModelDeployment"`)
- Auth trust caveat in code comments: `x-ms-client-principal-name` read verbatim. Gate on `x-ms-client-principal-id` presence; document without EasyAuth, caller can spoof identity.

**Test note:** Mock async paginators as async generators or `AsyncMock` returning `AsyncIterator` (different from single-value awaitable in existing tests).

---

### Decision 4: Frontend Design Review — APPROVE WITH CHANGES (Lambert, 2026-06-01)
**Status:** APPROVE WITH CHANGES — 3 must-fix, 4 design items

**Must-Fix Decisions:**

1. **Routing: drop hash route, use `showAdmin` boolean state**
   - No `react-router-dom` in `package.json`; hash route adds ~30 lines with no gain
   - Replace with `showAdmin: boolean` state in `App.tsx`, following `panelShowStates` pattern
   - Admin renders as full-viewport overlay (z-index above layout)
   - Trade-off: no deep-link support (acceptable for unauthenticated internal tooling)

2. **Gear icon visibility: hide behind env flag or query param**
   - Plan proposes visible gear icon to all users; no auth gate
   - Proposed: render only when `REACT_APP_SHOW_ADMIN=true` OR `?admin=1` query param (~3 lines code)
   - Env var for deployments; query param for local dev

3. **Stale-state (publish-while-editing) race condition — add ETag**
   - Backend `GET /api/admin/agent` must include `version_id` in response
   - Frontend stores `loadedVersionId` on fetch
   - `POST /api/admin/agent` body includes `{ instructions, model, expected_version_id: loadedVersionId }`
   - Backend returns 409 if current version ≠ expected
   - Frontend shows distinct MessageBar: *"Version v17 was published by [publisher] while you were editing. Discard changes or copy and reload."*
   - (Requires backend change; flagged for frontend contract)

**Design Items to Resolve Before Implementation:**

4. **Freeform Combobox validation strategy**
   - Models list loaded, typed value not in list: show inline warning but allow submit (Foundry gives clearer error)
   - Models list failed to load: show "Could not verify deployments" note; allow freeform entry without block

5. **Instructions textarea — three missing guards**
   - `maxLength` prop or truncation aligned with Foundry limit (typically 32,768 chars); counter as "X / 32,768 — at limit" in warning colour
   - Secret-pattern inline warning (not block): scan for `sk-`, connection strings, raw GUIDs; dismissible banner
   - Diff preview before publish: side-by-side or unified diff of textarea vs. current active instructions, inline or in drawer

6. **Publish flow: add confirm step**
   - Current: single Publish button, disabled if unchanged
   - Proposed: two-step Review → Confirm dialog with diff summary and "Publishing will update the live agent immediately"
   - Matches existing dialog pattern in `ChatHistoryPanel.tsx`
   - Trim whitespace before comparing (exact string compare enables Publish on whitespace-only edits)

7. **Rollback dialog — add instructions preview**
   - Call `GET /api/admin/agent/versions/{version_id}` on Rollback click
   - Show spinner, render target version instructions (truncated to ~500 chars + "show more") and model name before Confirm button
   - Users currently rolling back blind

8. **Version history table — pagination**
   - `GET /api/admin/agent/versions` could return hundreds of entries
   - Propose: default page size 20, "Load more" button at table bottom (matches `getHistoryListData` / offset pagination pattern)
   - Show most recent first (server-side `order_by=created_at desc`)

**Accessibility & Error Handling:**

9. **Explicit error messages per status code:**
   - 409: "Someone published a newer version while you were editing. Reload and re-apply changes."
   - 401: "You are not authorised to publish agent changes."
   - Network timeout: "Publish timed out — check backend logs. Agent may or may not have been updated."
   - Foundry validation error (4xx with body): surface Foundry's error verbatim in Details expander

10. **Accessibility requirements (not mentioned in plan):**
   - On admin panel open: move focus to panel `<h1>` or close button
   - On admin panel close: return focus to gear icon trigger
   - Success toast / MessageBar: add `role="status"` or `aria-live="polite"` for screen reader announcement
   - Version history Rollback buttons: `aria-label="Roll back to version {id}, published by {publisher} on {date}"`
   - Unsaved-changes warning (browser `beforeunload` or in-panel banner): visible to keyboard-only users

**Test Coverage Gaps:**
- Stale-state race: mock GET returns v16, publish returns 409, verify conflict MessageBar
- Model list load failure: mock `/api/admin/models` as 500, verify Combobox renders and doesn't block
- Freeform unknown model: verify warning appears but Publish not disabled
- Char-limit boundary: 32,769 chars, verify counter turns red
- Unsaved-changes: edit and navigate away, verify warning renders
- Rollback dialog: verify `GET /api/admin/agent/versions/{id}` called and preview renders
- 401 error: verify distinct message, not generic fallback

**Relationship to Ripley's Rejection:** Items 1–3 are **also blocking** from frontend side; must be resolved in plan revision regardless of backend concerns. Items 4–10 are design improvements for same revision pass.

---

### Decision 5: Test Strategy Review — APPROVE WITH CHANGES (Hicks, 2026-06-01)
**Status:** APPROVE WITH CHANGES

**Must-add test cases (blocking):**

1. Cache invalidation on successful publish — `agent_admin_service.publish()` must call `ChatService.invalidate_agent_cache()`; test with spy/mock. Plan describes feature but omits from Tests section.
2. Cache NOT invalidated on failed publish — `agents.create_version` raises → cache not cleared
3. Publisher attribution fallback — POST `/api/admin/agent` with no `x-ms-client-principal-name` header → publisher stored as `"local-dev"`
4. Rollback to non-existent version → 404, not 500
5. Foundry error mid-publish → 5xx with structured body `{"error": "<message>"}`, not unhandled traceback
6. Instructions edge cases: empty string → 422, whitespace-only → 422, over-length (if limit defined) → 422
7. Model name validation: empty string → 422, whitespace → 422
8. Models fallback path — `project_client.deployments.list()` raises `AttributeError` (SDK version lacks it) → fallback to management SDK path or empty list, not 500

**Should-add test cases (non-blocking):**

9. Concurrent publish race — two simultaneous POSTs; service must not corrupt cache state. Unit level: verify `invalidate_agent_cache()` is idempotent.
10. List versions empty state — Foundry returns empty list → endpoint returns `[]`, frontend renders "No versions yet"

**Parity invariants (from `01_create_agents.py`):**

Plan says (line 55): "smoke test that imports shared `agent_definition.py` and verifies tool names/params are unchanged."

Actual contract invariants required:
| Invariant | Expected value |
|---|---|
| FunctionTool name | `"get_sql_response"` |
| FunctionTool description | `"Execute T-SQL queries on the database to retrieve quantified, numerical, or metric-based data."` |
| FunctionTool param schema → type | `"object"` |
| FunctionTool param schema → required | `["sql_query"]` |
| FunctionTool param `sql_query` → type | `"string"` |
| AzureAISearch tool present | yes (exactly one) |
| AzureAISearch `query_type` | `"vector_simple"` |
| AzureAISearch `top_k` | `5` |
| Agent name template | `"KM-ConversationAgent-{solutionName}"` |
| Number of tools | exactly 2 |

Parity test must assert **all** of these, not just names.

**Mock fidelity concerns:**

`test_chat_service.py` patches `AIProjectClient` at class level using plain `MagicMock()`. Accessing `.agents.create_version(...)` on MagicMock auto-creates child MagicMock — call always succeeds and returns MagicMock regardless of real method existence or argument requirements.

- Tests can pass while real integration fails (wrong argument names)
- `list_versions` and `get_version` never called in `chat_service.py`; new tests must explicitly configure `AsyncMock` return values
- Must `assert_called_once_with(...)` to verify argument shape

**Recommended fix:** Create shared `pytest` fixture in `conftest.py` returning fully-typed `AsyncMock` for `AIProjectClient` with `.agents.create_version`, `.agents.list_versions`, `.agents.get_version`, `.deployments.list` explicitly configured. Both `test_chat_service.py` refactors and new `test_agent_admin_service.py` use it.

**Frontend test gaps:**

Plan says (line 56): "render page with mocked fetch responses, verify publish flow and rollback dialog."

Minimum additional RTL test cases:
| # | Test | Why |
|---|---|---|
| 1 | Publish button **disabled** when neither instructions nor model changed | Prevents accidental no-op publishes (stated UX rule, plan line 48) |
| 2 | Publish button **enabled** after editing instructions | Counterpart to above |
| 3 | Error `MessageBar` renders when `publishAgent` fetch returns 4xx/5xx | Error state rendering absent from plan |
| 4 | Char counter increments as user types in `Textarea` | Stated UX feature (plan line 47) |
| 5 | Model picker `Combobox` shows `Spinner` while `listModels` in-flight | Loading state for autocomplete |
| 6 | Version table renders "no versions" empty state when API returns `[]` | Empty state |
| 7 | Rollback confirmation dialog shows correct version info and closes on cancel | Plan mentions only "publish flow" explicitly tested |

**Note:** No existing DOM rendering test mirrors `App.test.tsx` (tests Redux reducer only). `AgentAdmin.test.tsx` will be project's first RTL component test. Needs `global.fetch` mock (via `jest.spyOn(global, 'fetch')` or MSW) consistent with `setupTests.ts`.

**Process suggestions:**

1. **Baseline-RED procedure missing:** Plan (line 57) says "Run baselines first" with no instruction if they fail. Add: "If baseline is RED, stop, triage failures, file issues before writing new tests. Do not proceed with feature tests against broken baseline."

2. **Pytest markers:** `pytest.ini` defines `unittest`, `functional`, `azure` markers. New tests must be tagged `@pytest.mark.unittest`. Real Foundry endpoint tests must be `@pytest.mark.azure` and excluded from CI baseline runs.

3. **Deterministic test data:** Use fixed version IDs (`"ver-0001"`, `"ver-0002"`) and ISO timestamps (`"2026-01-01T00:00:00Z"`). Do not use `MagicMock()` for fields the response body serializer touches — it will serialize to something unexpected.

4. **Integration test:** Plan proposes no end-to-end test. Add one `@pytest.mark.functional` integration test: `POST /api/admin/agent` → mock Foundry → `GET /api/admin/agent` → assert version matches. Exercises router-service-response pipeline without real Foundry connection; more valuable than route-only tests.

---

### Decision 6: Version 2 Plan Produced (Ripley, 2026-06-01)
**Status:** Proposed

**Summary:** Produced `plans/agent-admin-ui-v2.md` incorporating feedback from all reviews (Ripley architecture, Parker backend, Lambert frontend, Hicks tests).

**Key changes from v1:**
- v1 scope cut to instructions-only edit (no model picker, no version history)
- Auth gate mandatory: `x-ms-client-principal-id` required, 401 otherwise
- Cache TTL 3600s stated explicitly in plan and UI copy
- Concurrency: `expected_version_id` in PUT body, 409 on mismatch
- Conditional SDK sections for version history (gated on Parker's spike — now resolved)
- 9 parity invariants (up from 2)
- Frontend: panelShowStates pattern, no react-router-dom, Fluent v9 only
- First RTL component test in project

**Next steps:**
- Parker's SDK spike resolves conditional sections (✅ COMPLETED 2026-06-01)
- Implementation can begin on v1 scope immediately (no SDK dependency)

---

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
