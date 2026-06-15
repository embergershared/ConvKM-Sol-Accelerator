# Dashboard Drill-Down for Call Center Managers

## Problem
Today the Dashboard (`src/App/src/components/Chart/Chart.tsx`) shows 7 aggregate widgets — Total Calls, Avg Handle Time, Satisfied %, Sentiment donut, Avg Handle Time by Topic bar, Trending Topics table, Key Phrases word cloud — driven by `/api/fetchChartData[WithFilters]` against the `processed_data` and `processed_data_key_phrases` tables. A manager who spots an anomaly ("negative sentiment is up for Billing") can only respond by typing filters in `ChartFilter` and re-reading the same 7 aggregate widgets. There is no path from a chart element to the underlying conversations, and no way to see *trends over time* for a chosen slice.

The high-value workflow we want to enable: **see a KPI → see the trend → see the specific calls → read the transcript → ask the AI agent for a summary**, all without leaving the dashboard, in a small number of clicks.

## Approach — phased delivery

We ship in **two stages**. Stage B is the foundation (data layer + drill UI). Stage C layers cross-chart filtering and an AI handoff on top.

- **Stage B — Hierarchical drill (zoom-in):** Click a chart element → an overlay drawer opens showing **L1: time trend** for that selection → click a time bucket → **L2: call list** → click a row → **L3: transcript**. Breadcrumb at the top, back arrow and `Esc` pop one level; closing the drawer returns to the dashboard untouched. Other dashboard charts stay as-is.
- **Stage C — Cross-filter + AI handoff:** Single click on a chart mark now also **cross-filters** every other chart in place (Power BI–style); the drawer is opened via an explicit hover affordance ("▶ Investigate"). A persistent selection chip bar shows active drill state with `×` to remove. An **"Ask AI about this"** button in the drawer seeds the existing `Chat` panel with a context-aware prompt and opens it.

Stage C reuses every endpoint and component from Stage B; no rework required.

## Why this matters for a Call Center Manager
- **Trend detection in 1 click.** Today a manager only sees a topic's *average* handle time. After Stage B they see the time series and can spot the day the regression started.
- **Root-cause in 3 clicks.** Sentiment slice → topic week → individual call transcript with complaint highlighted.
- **AI summarization tied to evidence (Stage C).** "Summarize complaints for Billing flagged negative in the last 7 days" auto-routes to the existing `KM-ConversationAgent` with the drill context as the prompt, so the answer is grounded in the exact slice the manager is looking at.
- **Shareable investigations.** Drill state lives in the URL hash, so a manager can paste a link in Teams and a colleague lands on the same drilled view.

### Side effects / risks (designed-for, not optional)
- **SQL load.** Each drill issues a new query. A non-clustered composite index on `processed_data (mined_topic, sentiment, StartTime) INCLUDE (satisfied, EndTime)` keeps L1/L2 < 500 ms at expected sample-data scale. Recommended index ships as `infra/scripts/sqldb_drill_index.sql` and is documented in the README.
- **PII in transcripts.** `processed_data.Content` is the full call transcript. Currently `/api/*` data routes have no auth (`src/api/app.py` registers no auth middleware on `backend_router`). The transcript endpoint `/api/drill/call/{id}` is the first place this materially matters. **Decision (see Resolved decisions §1):** match the existing `admin_routes.py` pattern — `get_authenticated_user_details(request.headers)` is called on every drill endpoint and the resulting principal (or `"local-dev"` fallback) is attached to telemetry, but the endpoint does **not** refuse the request when headers are absent. Rationale: keeps drill consistent with every other backend route today; a stricter gate can be added as a single decorator later without touching call sites. Task `b-auth-decision` is therefore an implementation task (capture identity, emit `user_id` in every drill telemetry event), not an open decision.
- **State conflicts with `ChartFilter`.** Drill selections are a *filter delta* on top of the global filter. Both are visible in a single "Selections" pill bar (Stage C). For Stage B the drawer operates entirely on the dashboard's current filter set; closing the drawer does not modify global filters.
- **D3 click vs resize.** Existing D3 charts re-render on resize (`Chart.tsx` line 75-91). Click handlers must be added on the *post-render* selection inside the same `useEffect` block, not as a one-time wire-up. The existing tooltip pattern (`#tooltip-container` singleton in `HorizontalBarChart.tsx`) is reused.
- **A11y.** Every interactive D3 mark gets `role="button"`, `tabIndex=0`, `aria-label`, and an `Enter`/`Space` keyboard handler equivalent to the click. Fluent UI `OverlayDrawer`, `Breadcrumb`, and `DataGrid` carry the rest of the a11y burden.
- **Browser back.** Drill stack syncs to `window.location.hash` (mirror of the existing `#/admin` pattern in `App.tsx`). Browser back pops one drill level.
- **AI disclaimer.** The "AI-generated content may be incorrect" `Tag` at the bottom of `Chart.tsx` must also appear in the drill drawer footer and in any AI-generated summary inside it.
- **Stream race (Stage C).** Clicking "Ask AI about this" while another chat stream is in-flight: cancel the existing stream (`abortController`) before dispatching the new conversation.
- **Stage C double-click trap.** We explicitly avoid single vs double-click semantics. Cross-filter = plain click. Drawer = explicit "▶ Investigate" button revealed on chart tile hover (always-visible affordance on touch devices).

---

## Stage B — Hierarchical Drill (3 levels)

### Click matrix (what each chart element does)
| Source widget | Element clicked | Opens drawer at L1 with selection |
|---|---|---|
| Sentiment donut | Slice | `sentiment = <slice label>` |
| Avg Handling Time by Topic bar | Bar | `mined_topic = <bar category>` |
| Trending Topics table | Row | `mined_topic = <row.name>` |
| Key Phrases word cloud | Word | `key_phrase = <word>` (joins `processed_data_key_phrases`) |
| KPI cards (Total / AHT / Satisfied) | — | Not clickable in Stage B (no useful single-dimension selection). |

### Drill levels
- **L1 — Time trend.** Dual-axis chart for the chosen selection:
  - X: time bucket (auto: day if range ≤ 14 days, week otherwise; user toggle day/week).
  - Y-left: call volume (bar).
  - Y-right: avg sentiment score (line), where `positive=+1, neutral=0, negative=-1`, plus a satisfied-% overlay.
  - Click a bucket → push L2 with `time_range = bucket_start..bucket_end`.
- **L2 — Call list.** Fluent `DataGrid`, paginated (25 / page, max 100), sortable by start time / duration / sentiment. Columns: Start, Duration, Sentiment chip, Satisfied chip, Topic, Complaint flag, first 80 chars of summary, "View" button. Click any row or "View" → push L3.
- **L3 — Transcript.** Header: conversation id, start/end, sentiment chip, satisfied chip, topic, complaint badge, key phrase chips. Body: raw `Content` field rendered as a `<pre>` block for v1; structured speaker-turn parsing is a stretch goal flagged as `b-transcript-parser-stretch`.

### Drawer container
- Fluent v9 `OverlayDrawer` (`@fluentui/react-components`), `position="end"`, width `50%` on ≥ 1024 px, full-width on smaller. Mounted at the `Dashboard` root inside `App.tsx` so it overlays the whole panel layout.
- Header: `Breadcrumb` (`All › Topic: Billing › Week of 2026-05-25 › Call abc-123`), back arrow button (left), close X (right). `Esc` pops one level; closing at L1 closes the drawer.
- Footer: "AI-generated content may be incorrect" `Tag` + "Reset drill" link.

### Frontend state — new Redux slice
`src/App/src/state/slices/drillSlice.ts`:
```ts
type DrillSelection = {
  dimension: 'topic' | 'sentiment' | 'key_phrase';
  value: string;
};
type DrillLevel =
  | { kind: 'timeseries'; selection: DrillSelection; bucket: 'day'|'week' }
  | { kind: 'calls';      selection: DrillSelection; timeRange?: { from: string; to: string }; offset: number }
  | { kind: 'transcript'; conversationId: string };
type DrillState = {
  isOpen: boolean;
  stack: DrillLevel[];
  loading: boolean;
  error?: string;
  timeseries?: TimeseriesPoint[];
  calls?: { total: number; items: CallListItem[] };
  call?: CallDetail;
};
// actions: openDrill, pushLevel, popLevel, resetDrill, closeDrill, set{Timeseries,Calls,Call}, setLoading, setError
```
Hash sync: `useEffect` in `DrillDrawer` writes a compact encoding to `window.location.hash` (`#/drill/topic=Billing&bucket=week&from=2026-05-19&to=2026-05-25&call=abc`) and a `hashchange` listener restores state on load.

### Frontend — new files
- `src/App/src/state/slices/drillSlice.ts` — slice above; register in `src/App/src/state/store.ts`.
- `src/App/src/types/Drill.ts` — `DrillSelection`, `DrillLevel`, `TimeseriesPoint`, `CallListItem`, `CallDetail`.
- `src/App/src/components/Drill/DrillDrawer.tsx` — `OverlayDrawer` + breadcrumb + level switcher (`renderLevel(stack[stack.length-1])`).
- `src/App/src/components/Drill/TimeTrendChart.tsx` — d3, dual-axis, click on bucket → `dispatch(pushLevel({ kind: 'calls', ... }))`.
- `src/App/src/components/Drill/CallList.tsx` — Fluent `DataGrid`, server pagination through `fetchDrillCalls(..., offset)`.
- `src/App/src/components/Drill/CallTranscript.tsx` — header + raw transcript pre-block + "Open in Chat as context" placeholder button (no-op in Stage B; wired in Stage C).
- `src/App/src/components/Drill/drill.css` — colocated styling.

### Frontend — modified files
- `src/App/src/chartComponents/DonutChart.tsx` — accept `onSliceClick?: (label: string) => void`; in the d3 arc render add `.style('cursor', 'pointer')`, `.on('click', (_, d) => onSliceClick?.(d.data.label))`, `.attr('role','button').attr('tabindex','0').attr('aria-label', \`Drill into ${d.data.label}\`)`, and a `keydown` listener for Enter/Space.
- `src/App/src/chartComponents/HorizontalBarChart.tsx` — accept `onBarClick?: (category: string) => void` (use `d.fullCategoryText`, not the truncated `d.category`).
- `src/App/src/chartComponents/TopicTable.tsx` — row `onClick` + `role="button"` + `tabIndex`.
- `src/App/src/chartComponents/WordCloudChart.tsx` — accept `onWordClick?: (text: string) => void`.
- `src/App/src/components/Chart/Chart.tsx` — wire each chart's handler to `dispatch(openDrill({ selection: { dimension, value } }))`.
- `src/App/src/App.tsx` — render `<DrillDrawer />` inside the `FluentProvider` so it overlays both panel modes; extend the existing `hashchange` effect to also route `#/drill/...`.
- `src/App/src/state/store.ts` — register `drill` reducer.
- `src/App/src/api/api.ts` — add `fetchDrillTimeseries`, `fetchDrillCalls`, `fetchCallDetail`.

### Backend — new endpoints (router `src/api/api/drill_routes.py`, mounted at `/api/drill`)
| Method | Path | Body / params | Returns |
|---|---|---|---|
| POST | `/api/drill/timeseries` | `{ selection: { dimension, value }, bucket: 'day'|'week', filters: SelectedFilters }` | `[{ bucket_start, calls, avg_sentiment_score, satisfied_pct, avg_handle_time_min }]` |
| POST | `/api/drill/calls` | `{ selection, time_range?: { from, to }, filters, offset, limit }` | `{ total, items: [CallListItem] }` |
| GET | `/api/drill/call/{conversation_id}` | — | `CallDetail` (includes `Content` as `transcript_raw`) |

Mount in `src/api/app.py`:
```py
from api.drill_routes import router as drill_router
fastapi_app.include_router(drill_router, prefix="/api/drill", tags=["drill"])
```

### Backend — new files
- `src/api/api/drill_routes.py` — three handlers, identical try/except/track_event pattern as `api_routes.py:24-99`; on each request capture `get_authenticated_user_details(request.headers)` and add `user_id` to telemetry.
- `src/api/services/drill_service.py` — wraps the new SQL functions; `HTTPException` on errors mirroring `chart_service.py`.
- `src/api/api/models/input_models.py` — extend with `DrillSelection`, `DrillTimeseriesRequest`, `DrillCallsRequest` Pydantic models. Reuse the existing `SelectedFilters` (rename or alias if needed).

### Backend — modified files
- `src/api/common/database/sqldb_service.py` — three new async fns:
  - `fetch_drill_timeseries(selection, bucket, filters)` — `GROUP BY DATE_BUCKET(...)` over `processed_data` (or `processed_data_key_phrases` when `dimension='key_phrase'`) with parameterised `?` placeholders.
  - `fetch_drill_calls(selection, filters, time_range, offset, limit)` — `SELECT ... FROM processed_data WHERE ... ORDER BY StartTime DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY`; second query for `COUNT(*)`.
  - `fetch_call_detail(conversation_id)` — single-row select + join to `processed_data_key_phrases` for the phrase chips.
  - **All three use bound parameters** (the existing `fetch_chart_data` builds a string `where_clause` from enum-restricted filter values; new code must not extend that pattern).
- `src/api/app.py` — register `drill_router`.

### SQL
- Recommended index ships as `infra/scripts/sqldb_drill_index.sql`:
  ```sql
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_processed_data_topic_sentiment_time')
  CREATE NONCLUSTERED INDEX IX_processed_data_topic_sentiment_time
    ON [dbo].[processed_data] (mined_topic, sentiment, StartTime)
    INCLUDE (satisfied, EndTime, ConversationId);

  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_processed_data_key_phrases_phrase_time')
  CREATE NONCLUSTERED INDEX IX_processed_data_key_phrases_phrase_time
    ON [dbo].[processed_data_key_phrases] (key_phrase, StartTime)
    INCLUDE (ConversationId, sentiment, topic);
  ```
- Document under `infra/scripts/README` and chain into `run_sqldb_scripts.sh`.

### Telemetry
- Frontend: dispatch `appInsights.trackEvent({ name: 'DrillOpened' | 'DrillLevelChanged' | 'DrillCallViewed' | 'DrillResetClicked' | 'DrillBackPressed' })` with `{ dimension, value, level }` props.
- Backend: existing `track_event_if_configured` per endpoint with success/error variants, including `user_id` and selection dimension.

### Testing
- **Backend unit tests** — new directory `src/api/tests/` (none exist today; `pytest.ini` already sets `pythonpath = ./src/api`). Mark with `@pytest.mark.unittest`. Mock `get_db_connection`. Cases: filter pass-through, parameter binding (assert `cursor.execute` is called with the values list), pagination boundaries, empty result, unknown dimension → 400.
- **Frontend RTL** — Jest config already exists (`react-scripts test`). Tests:
  - `drillSlice.test.ts` — reducer transitions (open → push → pop → close), hash encode/decode round-trip.
  - `DrillDrawer.test.tsx` — renders correct level component based on stack top; `Esc` pops; breadcrumb item click pops to that depth.
  - `Chart.click.test.tsx` — donut/bar/row/word click dispatches `openDrill` with expected payload.
- **E2E (Playwright via the new `playwright` MCP server)** — add `tests/e2e-test/tests/test_drill_down.py` covering:
  1. Load dashboard → assert all 7 widgets.
  2. Click "Billing" bar in Avg Handle Time by Topic → drawer opens, breadcrumb shows `All › Topic: Billing`, time chart visible.
  3. Click last bucket → breadcrumb extends with week; call list visible; row count > 0.
  4. Click first row → transcript visible with header chips and raw text.
  5. Press `Esc` three times → drawer closed.
  6. URL hash round-trip: copy URL after step 3, open in new tab, drill state restores.

### Stage B success criteria
- All four chart click sources land at L1 in < 300 ms (median, sample data).
- L1 → L2 → L3 round-trip < 1.5 s (median, sample data, with the new indexes deployed).
- Drawer is keyboard-fully-operable (`Tab`, `Enter`, `Esc`).
- E2E spec passes locally and in `make e2e` (if defined).
- Existing dashboard, chat, citation, and admin flows show **zero behavioral regression** (RTL snapshots for `Chart.tsx` + visual smoke through e2e).

---

## Stage C — Cross-filter + AI Handoff

Builds on Stage B. No backend changes required *except* the optional auth/role gate from `b-auth-decision`.

> **Scope note (per Resolved decisions §1 & §3):** Stage C ships *without* `require_authenticated_user` on `/api/drill/*` (capture-only is sufficient) and *without* saved-view persistence (the URL hash extension covers sharing). The Stage C task list below reflects these cuts.

### Behaviors added
1. **Plain click on chart mark = cross-filter.** Dispatches an action that *adds* `{ dimension, value }` to the global ChartFilter selection and triggers `fetchChartDataWithFilters` for the whole dashboard. Existing manual `ChartFilter` panel state is preserved; the chip pill bar marks chart-originated chips with a small chart-icon prefix.
2. **Explicit "▶ Investigate" affordance per chart tile.** Always visible on touch; on hover for pointer. Clicking opens the Stage B drawer scoped to the most recent click in that chart (or the highest-value mark — e.g., top bar — if none has been clicked yet).
3. **Selection pill bar** above the dashboard grid. Each chip shows `<dimension>: <value>` with `×` to remove. "Reset all" clears manual + drill chips. Chip ordering: manual first, drill second.
4. **"Ask AI about this" button** in `DrillDrawer` header. On click:
   - Build a prompt from breadcrumb context. Examples:
     - L1: *"Summarize the main customer concerns in calls about {topic} (sentiment={sentiment_filter}) over the last {window}. Highlight the top 3 themes and any complaints flagged."*
     - L2 with time bucket: *"There were {n} calls about {topic} during {bucket_start}–{bucket_end}. Summarize the most common reasons for dissatisfaction and propose two coaching recommendations."*
     - L3 (single transcript): *"Read the attached transcript (Conversation {id}). Summarize the customer's complaint, the agent's resolution, and rate the agent's empathy on a scale of 1-5 with one-line reasoning."*
   - Cancel any in-flight chat stream via the existing `abortController` in `chatSlice`.
   - `dispatch(startNewConversation())`, then dispatch a synthetic user message with the prompt; existing `Chat` panel renders the stream as usual. If the dashboard panel was hidden, restore the three-column layout first.
5. **Extended URL hash.** Selection state encoded into hash so a link reproduces both the cross-filter chips and any open drill.
6. **(Stretch) Saved views.** Persist `{ filters, drill }` snapshots per user in a new Cosmos container `dashboardViews`. Out of scope for Stage C v1; flagged as `c-saved-views-stretch`.

### Frontend — modified files (additions)
- `src/App/src/state/slices/dashboardSlice.ts` — extend `selected_filters` reducer to accept programmatic additions tagged with a `source: 'manual' | 'chart'` discriminator. Also add a `pillBar` selector for the chip strip.
- `src/App/src/components/ChartFilter/ChartFilter.tsx` — render the unified pill bar above the dashboard grid, including chart-origin chips. Cross-filter additions reuse the existing `applyFilters` path.
- `src/App/src/components/Chart/Chart.tsx` — when a chart's click handler fires from Stage C, route to cross-filter instead of `openDrill`. Investigate button (`<Button icon={<OpenRegular />}>Investigate</Button>`) added to each `chart-item` header.
- `src/App/src/components/Drill/DrillDrawer.tsx` — `<Button appearance="primary" icon={<SparkleRegular/>}>Ask AI about this</Button>` in header; on click, build prompt from current `stack` and dispatch to chat.
- `src/App/src/state/slices/chatSlice.ts` — expose `seedAndSend(prompt: string)` thunk that aborts any in-flight stream, calls `startNewConversation()`, and dispatches the prompt.
- `src/App/src/configs/drillPrompts.ts` — prompt template registry keyed by drill level + dimension.

### Backend — modified files
- _None._ Per Resolved decisions §1, Stage C does **not** add a `require_authenticated_user` dependency. The capture-only identity wiring already lives in Stage B's `b-auth-decision`. All Stage C work is frontend-only.

### Stage C success criteria
- Plain click on any chart mark adds a chip in the pill bar and re-renders all 7 widgets filtered, in < 1 s (median).
- "▶ Investigate" opens the drawer scoped to the chosen mark.
- "Ask AI about this" produces a streaming AI answer in the existing Chat panel within 5 s of click.
- Pasting a copied URL reproduces filter chips + drill stack.
- No regression in Stage B behavior or in any existing dashboard / chat flow.

---

## Resolved decisions (2026-06-15)
All three previously-open questions have been resolved with the plan's default answer. Recorded here so the rationale survives outside the chat.

1. **Auth gate for `/api/drill/*`** — **Decision: capture-only, no gate. Match existing `admin_routes` pattern.**
   - Every drill endpoint calls `get_authenticated_user_details(request.headers)` and emits the resolved principal (or `"local-dev"`) as `user_id` in telemetry. None of the three endpoints refuse a request when principal headers are absent.
   - This keeps the drill routes consistent with every other backend route today (`admin_routes.py:38-48`, `api_routes.py`, `history_routes.py`). A stricter gate (e.g., `Depends(require_authenticated_user)`) can be added later as a single dependency on the router without touching service or route bodies.
   - Implication: task `b-auth-decision` becomes a small **implementation** task — wire `get_authenticated_user_details` into the 3 handlers and add `user_id` to telemetry events — not a design decision. Removed from Stage C's task list (no `require_authenticated_user` dependency to add).

2. **AI prompt templates for "Ask AI about this"** — **Decision: in code only for v1, in `src/App/src/configs/drillPrompts.ts`.**
   - The template registry is a plain TypeScript object keyed by drill level + dimension. No Admin UI surface, no runtime configurability in v1.
   - A future iteration can hoist the registry into the existing Admin UI (mirroring the agent-instructions pattern at `infra/scripts/agent_scripts/agent_instructions.py` + `Admin/AgentAdmin.tsx`) once telemetry shows the feature is used and which templates are popular.
   - Implication: no backend, schema, or Admin UI work in Stage C for prompts. `c-prompt-templates` is a single file addition.

3. **Saved views (filter + drill snapshots)** — **Decision: dropped from v1 entirely.**
   - The URL-hash sync built in Stage B (`#/drill/...`) and extended in Stage C (cross-filter chips + drill stack) already covers the "share a view with a colleague" workflow.
   - No Cosmos container, no per-user list, no localStorage fallback in v1. Re-evaluate after telemetry shows whether managers paste/bookmark hash URLs (`DrillOpened`, `CrossFilterApplied` events with `referrer === 'hash'` flag).
   - Implication: `c-saved-views-stretch` is **cut from scope**, not merely deferred. Removed from the Stage C task list below.

---

## Task list

Stage B (sequential dependencies in parentheses):

| ID | Title | Depends on |
|---|---|---|
| `b-auth-decision` | Wire `get_authenticated_user_details` into all 3 `/api/drill/*` handlers and add `user_id` to every drill telemetry event (capture-only, matches `admin_routes.py:38-48`). | — |
| `b-schema-validate` | Confirm `processed_data` / `processed_data_key_phrases` columns and ship `infra/scripts/sqldb_drill_index.sql` + doc | — |
| `b-backend-models` | Add `DrillSelection`, `DrillTimeseriesRequest`, `DrillCallsRequest` to `api/models/input_models.py` | — |
| `b-backend-sql` | Add `fetch_drill_timeseries`, `fetch_drill_calls`, `fetch_call_detail` in `sqldb_service.py` with parameterised queries | `b-backend-models` |
| `b-backend-service` | Create `services/drill_service.py` mirroring `chart_service.py` error handling | `b-backend-sql` |
| `b-backend-routes` | Create `api/drill_routes.py`, mount at `/api/drill` in `app.py`, telemetry events | `b-backend-service`, `b-auth-decision` |
| `b-backend-tests` | New `src/api/tests/test_drill_service.py` + `test_drill_routes.py` (pytest, `@unittest` mark) | `b-backend-routes` |
| `b-frontend-types` | `types/Drill.ts` | — |
| `b-frontend-api` | Add 3 fetch fns in `api/api.ts` | `b-frontend-types`, `b-backend-routes` |
| `b-frontend-slice` | `drillSlice.ts`, hash sync utility | `b-frontend-types` |
| `b-frontend-chart-handlers` | Wire click + keyboard handlers in 4 chart components + `Chart.tsx` dispatch | `b-frontend-slice` |
| `b-frontend-drawer` | `DrillDrawer.tsx` (Fluent OverlayDrawer + Breadcrumb + Esc + footer disclaimer) | `b-frontend-slice` |
| `b-frontend-timetrend` | `TimeTrendChart.tsx` (d3 dual-axis, bucket click → push L2) | `b-frontend-drawer`, `b-frontend-api` |
| `b-frontend-calllist` | `CallList.tsx` (Fluent DataGrid, pagination, sort) | `b-frontend-drawer`, `b-frontend-api` |
| `b-frontend-transcript` | `CallTranscript.tsx` (header chips, raw transcript block) | `b-frontend-drawer`, `b-frontend-api` |
| `b-frontend-hash` | Extend `App.tsx` `hashchange` effect for `#/drill/*`; restore stack from hash on load | `b-frontend-slice` |
| `b-telemetry` | Front + back drill events (`DrillOpened`, etc.) | `b-frontend-drawer`, `b-backend-routes` |
| `b-tests-frontend` | RTL: `drillSlice.test.ts`, `DrillDrawer.test.tsx`, `Chart.click.test.tsx` | `b-frontend-drawer`, `b-frontend-chart-handlers` |
| `b-e2e-playwright` | `tests/e2e-test/tests/test_drill_down.py` (via `playwright` MCP for authoring; CI runs existing pytest) | `b-tests-frontend`, `b-backend-tests` |
| `b-docs` | Update `README.md`, `Emm-README.md`, `documents/TechnicalArchitecture.md`, add a `Emm-Demo-prompts.md` walkthrough section | `b-e2e-playwright` |
| `b-transcript-parser-stretch` | (Stretch) Parse `Content` into speaker turns | `b-frontend-transcript` |

Stage C:

| ID | Title | Depends on |
|---|---|---|
| `c-precedence-design` | Spec single-click cross-filter, Investigate affordance, pill bar UX | All Stage B |
| `c-frontend-pillbar` | Unified pill bar in `ChartFilter` with `source` discriminator | `c-precedence-design` |
| `c-frontend-crossfilter` | Plain click on chart marks dispatches cross-filter, not drill | `c-frontend-pillbar`, `b-frontend-chart-handlers` |
| `c-frontend-investigate-btn` | Hover/always-on Investigate button per chart tile | `c-frontend-crossfilter` |
| `c-prompt-templates` | `configs/drillPrompts.ts` template registry | `c-precedence-design` |
| `c-frontend-ai-handoff` | "Ask AI about this" → abort current stream → `seedAndSend(prompt)` → restore Chat panel | `c-prompt-templates`, `b-frontend-drawer` |
| `c-hash-extended` | Extend URL hash to include cross-filter chips + drill stack | `c-frontend-crossfilter`, `b-frontend-hash` |
| `c-telemetry` | `CrossFilterApplied`, `InvestigateClicked`, `AIHandoffClicked` events | `c-frontend-ai-handoff` |
| `c-e2e` | Playwright spec: click bar → cross-filter → Investigate → Ask AI → assert chat stream | `c-frontend-ai-handoff`, `c-telemetry` |
| `c-docs` | Update README + TRANSPARENCY_FAQ (AI handoff is now more prominent) | `c-e2e` |

> Per Resolved decisions §3, `c-saved-views-stretch` is **cut from scope**, not deferred. URL-hash sharing covers the v1 use case.

---

## MCP servers leveraged during implementation
- **microsoft-docs** — Fluent UI v9 `OverlayDrawer` / `Breadcrumb` / `DataGrid` API; Azure SQL indexing & query-plan guidance; App Service telemetry quotas.
- **context7** — D3 v7 click + keyboard binding patterns without re-render thrash; Redux Toolkit slice patterns; React Testing Library async query patterns.
- **azure** — `bestpractices` tool for SQL DB scaling; live check of telemetry pipeline; verify `processed_data` index exists post-deploy.
- **sequential-thinking** — used to validate the click-matrix decomposition before authoring tasks (above).
- **playwright** — authoring + running the e2e drill spec (`b-e2e-playwright`, `c-e2e`).
