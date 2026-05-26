# Dashboard drill-down: cross-filter + conversation drill-through

## Problem
The dashboard (`src/App/src/components/Chart/Chart.tsx`) renders D3-based
charts (`DonutChart`, `HorizontalBarChart`, `WordCloudChart`, `TopicTable`,
`Card`) that are read-only with hover tooltips only. The only way to narrow
data is the global `ChartFilter` bar
(`src/App/src/components/ChartFilter/ChartFilter.tsx`), and there is no way
to inspect the individual conversations behind a chart slice. Users want to
drill down — both to slice the dashboard interactively and to read the
underlying conversations.

## Approach
Deliver drill-down in **two complementary layers**:

1. **Cross-filter (front-end only).** Clicking a chart element applies that
   value as a filter to every chart on the dashboard. Clicking the same
   element again toggles it off. Reuses the existing Redux `dashboardSlice`,
   `SelectedFilters` shape, and `/api/fetchChartDataWithFilters` endpoint —
   no backend changes.
2. **Conversation drill-through (new endpoints + new panel).** A "View
   conversations" trigger opens a left-sliding panel — reusing the
   `CitationPanel` pattern — that shows:
   - **Step 1 — Summary list:** a header summarizing the active filter
     context (e.g., *"47 conversations · Topic: Billing · Negative · Last 14
     days"*) followed by one card per conversation with date, duration,
     sentiment, topic, satisfied badge, and the AI `summary`.
   - **Step 2 — Full conversation:** clicking a summary card replaces the
     panel body with the full transcript (`Content`) + metadata, with a Back
     arrow returning to the list (list state preserved).

Both layers operate on the same `SelectedFilters` contract.

## Scope
- **Cross-filter dimensions:** `Topic`, `Sentiment`, `DateRange` only.
  `WordCloudChart` and `Card` stay non-interactive (their values don't map
  to existing filter dimensions).
- **Clearing the cross-filter:** click the same element again; the existing
  `Reset` button continues to clear everything.
- **Conversation panel trigger:** explicit "View conversations" button next
  to Apply in `ChartFilter`. Per-chart inline trigger (icon on hover over a
  bar/row) is a stretch goal — toolbar trigger ships first.

## Layer 1 — Click-to-cross-filter

### Element → filter mapping
| Chart | Click target | Filter dimension | Value source |
|---|---|---|---|
| `DonutChart` (sentiment) | arc | `Sentiment` | slice label, normalized via `filtersMeta.Sentiment` lookup |
| `HorizontalBarChart` (topic minutes) | bar | `Topic` | `Topic.key` resolved from `fullCategoryText` (NOT the truncated label) |
| `TopicTable` row | row | `Topic` | `Topic.key` |
| `WordCloudChart`, `Card` | — | n/a | non-interactive |

### Behavior
- A single `handleDrillDown(dimension, value)` in `Chart.tsx` reads
  `selectedFilters` from Redux, applies a toggle, dispatches
  `setSelectedFilters`, and calls the existing `applyFilters` path (which
  calls `fetchChartDataWithFilters`).
- **Toggle rules** (centralized in a `toggleFilterValue(current, value, mode)`
  helper):
  - `Sentiment` is single-select today. If the clicked value is already
    selected → reset to `"All"`. Otherwise replace.
  - `Topic` is multi-select today. If the value is already in the array →
    remove it. Otherwise append.
  - `DateRange` is reached only via the filter bar (no chart maps to it),
    but the helper still handles it as single-select.
- `ChartFilter` is already Redux-reactive; its chips/checkmarks update
  automatically when `selectedFilters` changes, giving users a visible
  indicator and a second way to clear from the bar.
- **Affordances:** `cursor: pointer` on clickable marks, hover emphasis,
  `.is-active` highlight for the currently-selected mark. Accessibility:
  `role="button"`, `tabindex="0"`, `aria-pressed`, keyboard activation on
  `Enter` and `Space`. Update tooltip to include a `(click to filter)` hint.

### Files (Layer 1)
- `src/App/src/configs/Utils.ts` — add `toggleFilterValue(current, value, mode)`.
- `src/App/src/components/Chart/Chart.tsx` — add `handleDrillDown`; pass
  `onDrillDown` + `activeValues` props in each `renderChart` case.
- `src/App/src/chartComponents/DonutChart.tsx` — accept `onDrillDown?`,
  `activeValue?`; wire arc clicks and active-arc styling.
- `src/App/src/chartComponents/HorizontalBarChart.tsx` — accept
  `onDrillDown?`, `activeValues?`; wire bar clicks using `fullCategoryText`.
- `src/App/src/chartComponents/TopicTable.tsx` — accept `onDrillDown?`,
  `activeValues?`; wire row click + keyboard handler + row highlight.
- `src/App/src/components/Chart/Chart.css` (and per-component CSS as needed)
  — `cursor: pointer`, hover, `.is-active` rules.

## Layer 2 — Conversation drill-through panel

### Backend (additive — no breaking changes)

Data source: `[dbo].[processed_data]` (schema in
`infra/scripts/index_scripts/03_cu_process_data_text.py:295`):
`ConversationId, EndTime, StartTime, Content, summary, satisfied, sentiment,
topic, key_phrases, complaint, mined_topic`. All fields needed by both panel
views exist on this single table — no joins required.

Two new endpoints, mirroring the structure and telemetry of the existing
chart endpoints in `src/api/api/api_routes.py`:

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| `POST` | `/api/fetchConversationList` | `{ selected_filters: ChartFilters, offset?: int = 0, limit?: int = 50 }` | `{ total: int, items: ConversationListItem[] }` |
| `GET`  | `/api/fetchConversationDetail` | `?conversation_id=...` | `ConversationDetail` (full row including `Content`) or 404 |

**`ConversationListItem`** (small payload — no `Content`):
```jsonc
{
  "conversation_id": "...",
  "start_time": "2025-04-01T13:22:00",
  "end_time": "2025-04-01T13:29:00",
  "duration_minutes": 7,
  "sentiment": "Negative",
  "topic": "Billing",            // mined_topic
  "satisfied": "no",
  "summary": "Customer disputed a duplicate charge ..."
}
```

**`ConversationDetail`** adds `content` (full transcript), `key_phrases`,
`complaint`.

**Implementation notes:**
- Add `fetch_conversation_list(filters, offset, limit)` and
  `fetch_conversation_detail(conversation_id)` in
  `src/api/common/database/sqldb_service.py`. **Reuse the existing
  `ChartFilters` WHERE-clause builder** that `fetch_chart_data` already
  uses (`sqldb_service.py:171`) so filter semantics are identical. Use
  parameterized SQL — never concatenate filter values.
- Pagination via `OFFSET ... ROWS FETCH NEXT ... ROWS ONLY` (SQL Server).
  Order by `StartTime DESC, ConversationId` for stable paging. Return
  `total` via a second `COUNT(*)` query against the same WHERE clause.
- Service layer: add methods to `ChartService` in
  `src/api/services/chart_service.py` (or split into a new
  `conversation_service.py` — prefer extending `ChartService` to minimize
  surface area). Wrap exceptions with `HTTPException` like the existing
  methods.
- Routes use the existing input model from `src/api/api/models/input_models.py`
  — extend it with an optional pagination wrapper model
  (`ConversationListRequest { selected_filters: ChartFilters, offset, limit }`)
  rather than overloading `ChartFilters`.
- Telemetry: emit `FetchConversationListSuccess` / `FetchConversationListError`
  and `FetchConversationDetailSuccess` / `FetchConversationDetailError` via
  `track_event_if_configured`, matching the existing pattern in
  `api_routes.py`.
- Sanitize NaN/Inf in the list response the same way
  `fetch_chart_data_with_filters` does.

### Front-end

**New API client** in `src/App/src/api/api.ts`:
- `fetchConversationList(filters: SelectedFilters, offset = 0, limit = 50)`
- `fetchConversationDetail(conversationId: string)`

Use the existing `httpClient` + `retryRequest` helpers and the same
NaN-handling pattern as `fetchChartDataWithFilters`.

**New Redux slice** `src/App/src/state/slices/conversationDrilldownSlice.ts`:
```ts
type ConversationDrilldownState = {
  open: boolean;
  view: 'list' | 'detail';
  activeFiltersSnapshot: SelectedFilters | null;
  list: {
    loading: boolean;
    error: string | null;
    total: number;
    items: ConversationListItem[];
    offset: number;
    pageSize: number;
    hasMore: boolean;
  };
  detail: {
    loading: boolean;
    error: string | null;
    conversationId: string | null;
    data: ConversationDetail | null;
  };
};
```
Action creators: `openDrilldown(filtersSnapshot)`, `closeDrilldown()`,
`viewConversation(id)`, `backToList()`, plus async thunks
`fetchConversationListThunk` (initial + paged) and
`fetchConversationDetailThunk`. Register the reducer in
`src/App/src/state/store.ts`.

**New component** `src/App/src/components/ConversationDrilldownPanel/`:
- `ConversationDrilldownPanel.tsx` + `ConversationDrilldownPanel.css`
- Reuses the `CitationPanel` slide-from-left pattern (see
  `src/App/src/components/CitationPanel/CitationPanel.css`). If extracting a
  shared `SlidePanel` chrome cleanly serves both panels without regressions,
  do so; otherwise duplicate the proven pattern to avoid destabilizing the
  existing citation panel.
- **Step 1 (list):**
  - Sticky header: title "Conversations" + Dismiss button (mirrors
    `CitationPanel.tsx:21-50`).
  - Subheader: filter chips ("Topic: Billing", "Sentiment: Negative",
    date range) + total count (`"47 conversations"`).
  - List of `ConversationCard` items: date, duration, sentiment pill
    (reuse `getSentimentColor`), topic chip, satisfied badge, summary
    (clamped to 3 lines + "Read more" → opens step 2).
  - Lazy-load next page on scroll (`hasMore && !loading`).
  - Loading skeletons, empty state ("No conversations match these filters"),
    error state with retry.
- **Step 2 (detail):**
  - Header: Back arrow → `backToList()`, conversation metadata (id, date,
    duration, sentiment pill, topic, satisfied), "Copy ID" button.
  - Body: full transcript rendered with `ReactMarkdown` + `remark-gfm`
    (same libs as `CitationPanel`).
  - Loading skeleton, error state with retry.

**Trigger UI** in `src/App/src/components/ChartFilter/ChartFilter.tsx`:
- Add a `DefaultButton` "View conversations" next to the existing Apply
  button. On click: dispatch `openDrilldown(selectedFilters)` and trigger
  `fetchConversationListThunk` with `offset=0`.
- Disabled while `fetchingCharts` is true.

**Mount point:** render `<ConversationDrilldownPanel />` from `App.tsx`
alongside `CitationPanel`. If both are open simultaneously, prefer the
conversation panel on the dashboard view and the citation panel on the chat
view (z-index + a single small selector based on the active tab — keep
simple).

**Coexistence:** changing dashboard filters while the panel is open should
refetch the list against the new snapshot and reset to step 1.

### Files (Layer 2)
**Backend:**
- `src/api/common/database/sqldb_service.py` — `fetch_conversation_list`,
  `fetch_conversation_detail` (parameterized; reuse WHERE-clause builder).
- `src/api/api/models/input_models.py` — `ConversationListRequest`.
- `src/api/services/chart_service.py` — `fetch_conversation_list`,
  `fetch_conversation_detail` service methods.
- `src/api/api/api_routes.py` — two new endpoints + telemetry.

**Frontend:**
- `src/App/src/api/api.ts` — two new client functions + types.
- `src/App/src/types/AppTypes.ts` — `ConversationListItem`,
  `ConversationDetail`.
- `src/App/src/state/slices/conversationDrilldownSlice.ts` — new slice.
- `src/App/src/state/store.ts` — register slice.
- `src/App/src/components/ConversationDrilldownPanel/` — new component +
  CSS.
- `src/App/src/components/ChartFilter/ChartFilter.tsx` — "View
  conversations" trigger.
- `src/App/src/App.tsx` — mount the panel.
- (Optional) `src/App/src/components/SlidePanel/` — shared slide-in chrome
  if extractable cleanly.

## Testing
- **Unit (front-end):**
  - `toggleFilterValue` — single/multi, add/remove, default fallback.
  - `conversationDrilldownSlice` — reducers + thunks (mock `api.ts`).
  - Each chart component — `onDrillDown` fires with correct value on click
    + keyboard; `activeValues` renders `.is-active` class.
  - `ConversationDrilldownPanel` — loading/empty/error/list/detail states;
    list-item click → detail; Back → list; Dismiss closes.
- **Integration (front-end):** "View conversations" flow dispatches list
  fetch with the current `SelectedFilters`; item click triggers detail
  fetch.
- **Back-end:** add tests under `src/api/tests` (or the existing tests
  location — match neighbors) mirroring the existing chart-endpoint test
  style. Cover: filter parameterization, pagination, total accuracy, 404
  on unknown `conversation_id`, telemetry events emitted, parameterized SQL
  (no injection surface).
- Run `npm test` in `src/App` and `pytest` for back-end to catch
  regressions.

## Out of scope (explicit)
- New filter dimensions (e.g., keyword/word-cloud drill).
- Audio playback for conversations (only text `Content` is shown).
- Editing conversations or adding annotations.
- URL deep-links / shareable drill-down state.
- Persisting drill-down state across reloads.
- Per-chart inline "View conversations" affordance is a stretch goal; the
  toolbar trigger ships first.

## Notes / considerations
- **Schema source of truth:** `[dbo].[processed_data]` defined in
  `infra/scripts/index_scripts/03_cu_process_data_text.py:295`. The `km_processed_data`
  table holds the same data post-mining; using `processed_data` (which the
  existing `fetch_chart_data` queries) keeps the filter WHERE clauses
  consistent across endpoints.
- **Bar chart label truncation:** `HorizontalBarChart` truncates labels
  (`category.substring(0, 20) + "..."`); always use `fullCategoryText` when
  resolving back to a `Topic.key` for drill-down.
- **Sentiment casing:** the donut display lowercases via
  `getSentimentColor`, but the filter contract uses
  `Positive`/`Neutral`/`Negative`. Normalize via `filtersMeta.Sentiment`
  lookup before dispatching.
- **Payload size:** `Content` (transcript) may be large — list endpoint
  must NOT include it; only the detail endpoint returns it.
- **Coexistence with `CitationPanel`:** both are left-sliding panels but
  belong to different tabs (dashboard vs. chat). Single active tab at a
  time today, so a simple z-index/precedence rule is sufficient.

## Implementation order (suggested)

1. Layer 1 — cross-filter (independent, ships value quickly):
   `toggle-helper` → `chart-handler` → (`donut-click`, `bar-click`,
   `table-click`) → `css-affordance` → `tests-charts`.
2. Layer 2 — back end first:
   `backend-list-endpoint` → `backend-detail-endpoint` → `backend-tests`.
3. Layer 2 — front end:
   `api-client` → `drill-slice` → (`drill-panel`, `drill-trigger`) →
   `drill-mount` → `drill-tests`.

## Todo checklist

### Layer 1 — cross-filter
- [ ] **toggle-helper** — Add `toggleFilterValue(current, value, mode)` in
  `src/App/src/configs/Utils.ts`. Single-select replaces or clears to
  default (Sentiment → `"All"`); multi-select adds/removes. Unit tested.
- [ ] **chart-handler** — In `src/App/src/components/Chart/Chart.tsx` build
  `handleDrillDown(dimension, value)`. Reads `selectedFilters` from Redux,
  calls `toggleFilterValue`, dispatches `setSelectedFilters`, calls
  existing `applyFilters`. Passes `onDrillDown` + `activeValues` to chart
  components in `renderChart`. (Depends on: toggle-helper)
- [ ] **donut-click** — In `src/App/src/chartComponents/DonutChart.tsx`
  add D3 arc click, `cursor: pointer`, hover emphasis, role/tabindex/
  keyboard activation; highlight active slice via `activeValue` prop.
  (Depends on: chart-handler)
- [ ] **bar-click** — In `src/App/src/chartComponents/HorizontalBarChart.tsx`
  wire bar click using `fullCategoryText` (untruncated); hover/active
  styles, a11y, keyboard activation; `activeValues` prop. (Depends on:
  chart-handler)
- [ ] **table-click** — In `src/App/src/chartComponents/TopicTable.tsx`
  wire row click + keyboard, hover/active styles, `role="button"` /
  `aria-pressed`, `activeValues` prop. (Depends on: chart-handler)
- [ ] **css-affordance** — `cursor: pointer`, hover, and `.is-active`
  highlight rules in `Chart.css` and per-component CSS so users see
  clickable and active elements. (Depends on: chart-handler)
- [ ] **tests-charts** — Tests: `toggleFilterValue` helper; `Chart.tsx`
  `handleDrillDown` dispatch + `applyFilters` payload; each chart
  component fires `onDrillDown` with correct value on click and keyboard;
  `activeValues` renders `.is-active` class. Run `npm test` in `src/App`.
  (Depends on: donut-click, bar-click, table-click)

### Layer 2 — backend
- [ ] **backend-list-endpoint** — New `POST /api/fetchConversationList` in
  `src/api/api/api_routes.py` + service method + new SQL function
  `fetch_conversation_list` in
  `src/api/common/database/sqldb_service.py`. Reuses existing
  `ChartFilters` WHERE-clause builder; selects `ConversationId, StartTime,
  EndTime, DATEDIFF(MINUTE, StartTime, EndTime), sentiment, mined_topic,
  satisfied, summary` from `[dbo].[processed_data]`. Supports `offset`/
  `limit` pagination; returns `total`. Telemetry matches existing chart
  endpoints. Parameterized SQL.
- [ ] **backend-detail-endpoint** — New `GET /api/fetchConversationDetail`
  in `src/api/api/api_routes.py` returning full row from
  `[dbo].[processed_data]` for a given `conversation_id`, including
  `Content` (full transcript), `summary`, `key_phrases`, `complaint`,
  `sentiment`, `topic`, times. 404 on unknown id. (Depends on:
  backend-list-endpoint)
- [ ] **backend-tests** — Mirror existing chart endpoint tests under
  `src/api`: filter parameterization, pagination, total accuracy, error
  cases, 404 on unknown `conversation_id`, telemetry events emitted.
  (Depends on: backend-list-endpoint, backend-detail-endpoint)

### Layer 2 — frontend
- [ ] **api-client** — In `src/App/src/api/api.ts` add
  `fetchConversationList(filters, offset, limit)` and
  `fetchConversationDetail(id)` using existing `httpClient` +
  `retryRequest` patterns. Add types in
  `src/App/src/types/AppTypes.ts`. (Depends on: backend-list-endpoint,
  backend-detail-endpoint)
- [ ] **drill-slice** — New Redux slice
  `src/App/src/state/slices/conversationDrilldownSlice.ts` with state
  shape described above; actions `openDrilldown`, `closeDrilldown`,
  `viewConversation`, `backToList`, plus async thunks for list + detail
  fetch. Register in `src/App/src/state/store.ts`. (Depends on:
  api-client)
- [ ] **drill-panel** — New
  `src/App/src/components/ConversationDrilldownPanel/` (tsx + css)
  reusing `CitationPanel` slide-in pattern. Step 1: summary header
  (filter chips + total) + paged list of summary cards. Step 2: Back
  arrow + transcript header + `ReactMarkdown` of `Content`. Loading
  skeletons + empty/error states. (Depends on: drill-slice)
- [ ] **drill-trigger** — Add "View conversations" `DefaultButton` in
  `src/App/src/components/ChartFilter/ChartFilter.tsx` next to Apply.
  Dispatches `openDrilldown` with current `selectedFilters` snapshot and
  triggers list fetch. (Depends on: drill-slice)
- [ ] **drill-mount** — Mount `<ConversationDrilldownPanel />` in
  `src/App/src/App.tsx` alongside `CitationPanel`; ensure z-index /
  coexistence rules so panels do not collide. (Depends on: drill-panel)
- [ ] **drill-tests** — Unit tests for the slice (reducers, async
  thunks), panel rendering across loading/empty/error/list/detail
  states, list-item click → detail, back navigation, dismiss. Mock
  `api.ts`. (Depends on: drill-panel, drill-trigger)
