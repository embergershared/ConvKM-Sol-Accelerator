import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type {
  CallDetail,
  CallListItem,
  DrillBucket,
  DrillLevel,
  DrillSelection,
  DrillTimeRange,
  TimeseriesPoint,
} from "../../types/Drill";

export type DrillState = {
  isOpen: boolean;
  stack: DrillLevel[];
  loading: boolean;
  error?: string;
  timeseries?: TimeseriesPoint[];
  calls?: { total: number; items: CallListItem[] };
  call?: CallDetail;
};

const initialState: DrillState = {
  isOpen: false,
  stack: [],
  loading: false,
};

const drillSlice = createSlice({
  name: "drill",
  initialState,
  reducers: {
    openDrill(
      state,
      action: PayloadAction<{ selection: DrillSelection; bucket?: DrillBucket }>
    ) {
      const bucket = action.payload.bucket ?? "week";
      state.isOpen = true;
      state.stack = [
        {
          kind: "timeseries",
          selection: action.payload.selection,
          bucket,
        },
      ];
      state.timeseries = undefined;
      state.calls = undefined;
      state.call = undefined;
      state.error = undefined;
      state.loading = false;
    },
    pushLevel(state, action: PayloadAction<DrillLevel>) {
      state.stack.push(action.payload);
      state.error = undefined;
      if (action.payload.kind === "calls") {
        state.calls = undefined;
      } else if (action.payload.kind === "transcript") {
        state.call = undefined;
      }
    },
    popLevel(state) {
      if (state.stack.length > 1) {
        const removed = state.stack.pop();
        if (removed?.kind === "transcript") {
          state.call = undefined;
        } else if (removed?.kind === "calls") {
          state.calls = undefined;
        }
      } else {
        state.isOpen = false;
        state.stack = [];
        state.timeseries = undefined;
        state.calls = undefined;
        state.call = undefined;
      }
      state.error = undefined;
    },
    popToDepth(state, action: PayloadAction<number>) {
      const depth = Math.max(1, Math.min(action.payload, state.stack.length));
      state.stack = state.stack.slice(0, depth);
      state.error = undefined;
      if (state.stack.length < 3) state.call = undefined;
      if (state.stack.length < 2) state.calls = undefined;
    },
    setBucket(state, action: PayloadAction<DrillBucket>) {
      const top = state.stack[0];
      if (top && top.kind === "timeseries") {
        top.bucket = action.payload;
        state.timeseries = undefined;
      }
    },
    setTimeRange(
      state,
      action: PayloadAction<DrillTimeRange | undefined>
    ) {
      const calls = state.stack.find((l) => l.kind === "calls") as
        | (DrillLevel & { kind: "calls" })
        | undefined;
      if (calls) {
        calls.timeRange = action.payload;
        calls.offset = 0;
        state.calls = undefined;
      }
    },
    setCallsOffset(state, action: PayloadAction<number>) {
      const calls = state.stack.find((l) => l.kind === "calls") as
        | (DrillLevel & { kind: "calls" })
        | undefined;
      if (calls) calls.offset = Math.max(0, action.payload);
    },
    resetDrill(state) {
      state.isOpen = false;
      state.stack = [];
      state.timeseries = undefined;
      state.calls = undefined;
      state.call = undefined;
      state.error = undefined;
      state.loading = false;
    },
    closeDrill(state) {
      state.isOpen = false;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
    },
    setError(state, action: PayloadAction<string | undefined>) {
      state.error = action.payload;
      state.loading = false;
    },
    setTimeseries(state, action: PayloadAction<TimeseriesPoint[]>) {
      state.timeseries = action.payload;
      state.loading = false;
      state.error = undefined;
    },
    setCalls(
      state,
      action: PayloadAction<{ total: number; items: CallListItem[] }>
    ) {
      state.calls = action.payload;
      state.loading = false;
      state.error = undefined;
    },
    setCall(state, action: PayloadAction<CallDetail>) {
      state.call = action.payload;
      state.loading = false;
      state.error = undefined;
    },
    restoreStack(
      state,
      action: PayloadAction<{ stack: DrillLevel[]; isOpen?: boolean }>
    ) {
      state.stack = action.payload.stack;
      state.isOpen = action.payload.isOpen ?? action.payload.stack.length > 0;
      state.timeseries = undefined;
      state.calls = undefined;
      state.call = undefined;
      state.error = undefined;
      state.loading = false;
    },
  },
});

export const {
  openDrill,
  pushLevel,
  popLevel,
  popToDepth,
  setBucket,
  setTimeRange,
  setCallsOffset,
  resetDrill,
  closeDrill,
  setLoading,
  setError,
  setTimeseries,
  setCalls,
  setCall,
  restoreStack,
} = drillSlice.actions;

export default drillSlice.reducer;
