# Hicks — History

## Project Context

- **Project:** ConvKM-Sol-Accelerator
- **Tech stack:** Python FastAPI backend (`src/api/`), React + TypeScript + Fluent UI v9 frontend (`src/App/`), Azure AI Foundry agents (`azure-ai-projects` SDK), Azure infra via azd/Bicep
- **User:** Emmanuel
- **Created:** 2026-06-01

## Learnings

### 2026-06-01 — Test strategy review: agent-admin-ui plan

**Source:** `plans/agent-admin-ui.md` lines 53–57, requested by Emmanuel.

**Key findings recorded for future work:**

1. **Mock surface for `AIProjectClient` is shallow.** All tests in `src/tests/api/services/test_chat_service.py` patch `AIProjectClient` at the class level and use raw `MagicMock()`. Accessing `.agents.create_version(...)` on a MagicMock auto-generates a child MagicMock — tests pass without validating SDK call signatures. New admin service tests must explicitly configure AsyncMock return values for `.agents.create_version`, `.agents.list_versions`, `.agents.get_version`, and `.deployments.list()` and assert on call arguments, not just that the mock was called.

2. **Parity contract with `01_create_agents.py` is richer than stated.** The plan says "verify tool names/params unchanged." The actual contract includes: FunctionTool name (`get_sql_response`), description string, parameter schema object (type/properties/required), AzureAISearch `query_type="vector_simple"`, `top_k=5`, and the agent name template `KM-ConversationAgent-{solutionName}`. A parity test must encode all of these, not just names.

3. **Cache invalidation test is missing entirely.** Plan describes `invalidate_agent_cache()` as a feature (line 36) but Tests section (lines 53–57) never mentions it. Need: publish-success → cache cleared, publish-failure → cache untouched.

4. **Frontend test baseline is effectively zero.** The only existing frontend test is `App.test.tsx` which tests a Redux reducer slice (no DOM rendering). `AgentAdmin.test.tsx` will be the first RTL component test in the project; needs careful setup with `global.fetch` mock or MSW.

5. **Pytest markers:** `pytest.ini` defines `unittest`, `functional`, `azure` markers. New admin service tests should be tagged `@pytest.mark.unittest`; any test that calls real Foundry APIs should be `@pytest.mark.azure`.

6. **No baseline-RED procedure.** Plan says run baselines first but gives no instruction if they fail. Must require a clean baseline before any new test work begins.

### 2026-06-01 — Plan review completed; v2 at plans/agent-admin-ui-v2.md; SDK confirmed via projects.AIProjectClient.agents (NOT agents.AgentsClient)

- Plan review session with ripley, parker, lambert for feedback; parker-1 SDK spike; ripley-1 v2 plan.
- Test strategy review approved with changes: 8 must-add test cases (blocking), parity invariants (9 items), mock fidelity fix (shared conftest fixture), frontend RTL test gaps, pytest markers, integration test.
- All test items incorporated into v2 plan with explicit test strategy section.
- v1 scope instructions-only; v2 scope gates on SDK (now confirmed).
- 6 decisions merged; orchestration/session logs created.
- Implementation ready on v1 scope with explicit test roadmap.
