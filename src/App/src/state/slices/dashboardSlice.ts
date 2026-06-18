import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
  type ChartConfigItem,
  type FilterMetaData,
  type SelectedFilters,
} from "../../types/AppTypes";
import { defaultSelectedFilters } from "../../configs/Utils";

// Stage C — cross-filter selections shown in the unified pill bar above the
// dashboard grid. Kept *parallel* to `selectedFilters` rather than reshaping
// it, so the backend payload sent to `/api/fetchChartDataWithFilters`
// (a flat Record<string, string[]>) is unchanged. The `source` discriminator
// lets the pill bar render chart-originated chips with a small icon prefix
// and lets "Reset all" know which chips it owns.
export type ChartFilterChipSource = "manual" | "chart";

export type ChartFilterChip = {
  dimension: string; // e.g. "Topic" | "Sentiment" | "key_phrase"
  value: string;
  source: ChartFilterChipSource;
};

export type DashboardState = {
  filtersMetaFetched: boolean;
  initialChartsDataFetched: boolean;
  filtersMeta: FilterMetaData;
  charts: ChartConfigItem[];
  selectedFilters: SelectedFilters;
  chartFilterChips: ChartFilterChip[];
  fetchingFilters: boolean;
  fetchingCharts: boolean;
};

const initialState: DashboardState = {
  filtersMetaFetched: false,
  initialChartsDataFetched: false,
  filtersMeta: {
    Sentiment: [],
    Topic: [],
    DateRange: [],
  },
  charts: [],
  selectedFilters: { ...defaultSelectedFilters },
  chartFilterChips: [],
  fetchingCharts: true,
  fetchingFilters: true,
};

// Cap the number of chips that survive an URL-hash round-trip. State is
// unbounded; the cap is enforced only by the hash encoder (drillHash.ts).
export const CHART_FILTER_CHIP_HASH_CAP = 10;

/**
 * Flatten chips back into the `SelectedFilters` shape expected by the
 * backend (`/api/fetchChartDataWithFilters` body). The optional `base` is
 * the existing manual ChartFilter state; chart-origin chips are merged on top
 * (deduped per dimension) so a user can cross-filter on top of their global
 * filter row.
 *
 * Special case for Sentiment: the manual filter row uses `["all"]` as a
 * "no filter" sentinel (see `defaultSelectedFilters` in configs/Utils.tsx).
 * `Chart.tsx`'s legacy `getChartData` empties the Sentiment array entirely
 * when its first element is "all", so a naive `["all", "Negative"]` merge
 * silently drops the Negative chip and the backend sees no sentiment filter
 * at all. We strip the sentinel here whenever a real Sentiment chip is added
 * so the merged payload reaches the backend intact.
 *
 * Lives next to the slice (rather than in `utils/`) because both the slice
 * and the Chart component need it and co-locating keeps imports terse.
 */
export function flattenChipsToSelectedFilters(
  chips: ChartFilterChip[],
  base?: SelectedFilters
): SelectedFilters {
  const out: SelectedFilters = { ...(base ?? {}) };
  for (const chip of chips) {
    const existing = out[chip.dimension];
    // Drop the "all" sentinel before merging real Sentiment values.
    const isAllSentinel =
      chip.dimension === "Sentiment" &&
      Array.isArray(existing) &&
      existing.length === 1 &&
      existing[0] === "all";

    if (isAllSentinel) {
      out[chip.dimension] = [chip.value];
      continue;
    }

    if (Array.isArray(existing)) {
      if (!existing.includes(chip.value)) {
        // Also strip any stray "all" entries mixed with real values.
        const cleaned =
          chip.dimension === "Sentiment"
            ? existing.filter((v) => v !== "all")
            : existing;
        out[chip.dimension] = [...cleaned, chip.value];
      }
    } else if (typeof existing === "string" && existing) {
      if (existing !== chip.value) {
        out[chip.dimension] = [existing, chip.value];
      }
    } else {
      out[chip.dimension] = [chip.value];
    }
  }
  return out;
}

const dashboardSlice = createSlice({
  name: "dashboards",
  initialState,
  reducers: {
    setFiltersMeta(state, action: PayloadAction<FilterMetaData>) {
      state.filtersMeta = action.payload;
    },
    setFiltersMetaFetched(state, action: PayloadAction<boolean>) {
      state.filtersMetaFetched = action.payload;
    },
    setChartsData(state, action: PayloadAction<ChartConfigItem[]>) {
      state.charts = action.payload;
    },
    setInitialChartsDataFetched(state, action: PayloadAction<boolean>) {
      state.initialChartsDataFetched = action.payload;
    },
    setSelectedFilters(state, action: PayloadAction<SelectedFilters>) {
      state.selectedFilters = action.payload;
    },
    setFetchingCharts(state, action: PayloadAction<boolean>) {
      state.fetchingCharts = action.payload;
    },
    setFetchingFilters(state, action: PayloadAction<boolean>) {
      state.fetchingFilters = action.payload;
    },
    resetSelectedFilters(state) {
      state.selectedFilters = { ...defaultSelectedFilters };
    },
    addChip(state, action: PayloadAction<ChartFilterChip>) {
      const incoming = action.payload;
      const exists = state.chartFilterChips.some(
        (c) =>
          c.dimension === incoming.dimension && c.value === incoming.value
      );
      if (!exists) state.chartFilterChips.push(incoming);
    },
    removeChip(
      state,
      action: PayloadAction<{ dimension: string; value: string }>
    ) {
      const { dimension, value } = action.payload;
      state.chartFilterChips = state.chartFilterChips.filter(
        (c) => !(c.dimension === dimension && c.value === value)
      );
    },
    clearChips(
      state,
      action: PayloadAction<ChartFilterChipSource | undefined>
    ) {
      const source = action.payload;
      if (!source) {
        state.chartFilterChips = [];
      } else {
        state.chartFilterChips = state.chartFilterChips.filter(
          (c) => c.source !== source
        );
      }
    },
    setChips(state, action: PayloadAction<ChartFilterChip[]>) {
      state.chartFilterChips = action.payload;
    },
  },
});

export const {
  setFiltersMeta,
  setFiltersMetaFetched,
  setChartsData,
  setInitialChartsDataFetched,
  setSelectedFilters,
  setFetchingCharts,
  setFetchingFilters,
  resetSelectedFilters,
  addChip,
  removeChip,
  clearChips,
  setChips,
} = dashboardSlice.actions;

export default dashboardSlice.reducer;
