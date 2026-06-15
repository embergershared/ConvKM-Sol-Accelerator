import drillReducer, {
  closeDrill,
  openDrill,
  popLevel,
  popToDepth,
  pushLevel,
  resetDrill,
  restoreStack,
  setBucket,
  setCallsOffset,
  setError,
  setLoading,
  setTimeRange,
} from "./drillSlice";
import type { DrillLevel } from "../../types/Drill";

const billingSelection = { dimension: "topic" as const, value: "Billing" };

describe("drillSlice", () => {
  it("openDrill seeds a timeseries level with the requested bucket", () => {
    const state = drillReducer(
      undefined,
      openDrill({ selection: billingSelection, bucket: "day" })
    );
    expect(state.isOpen).toBe(true);
    expect(state.stack).toHaveLength(1);
    const top = state.stack[0];
    expect(top.kind).toBe("timeseries");
    if (top.kind === "timeseries") {
      expect(top.bucket).toBe("day");
      expect(top.selection.value).toBe("Billing");
    }
  });

  it("pushLevel + popLevel produce a stack and unwind it", () => {
    let state = drillReducer(
      undefined,
      openDrill({ selection: billingSelection })
    );
    const callsLevel: DrillLevel = {
      kind: "calls",
      selection: billingSelection,
      timeRange: { from: "2024-12-01T00:00:00Z", to: "2024-12-08T00:00:00Z" },
      offset: 0,
    };
    state = drillReducer(state, pushLevel(callsLevel));
    state = drillReducer(
      state,
      pushLevel({ kind: "transcript", conversationId: "abc-1" })
    );
    expect(state.stack).toHaveLength(3);

    state = drillReducer(state, popLevel());
    expect(state.stack).toHaveLength(2);
    expect(state.stack[1].kind).toBe("calls");

    state = drillReducer(state, popLevel());
    expect(state.stack).toHaveLength(1);

    // Popping the last level closes the drawer entirely.
    state = drillReducer(state, popLevel());
    expect(state.isOpen).toBe(false);
    expect(state.stack).toHaveLength(0);
  });

  it("popToDepth trims to the requested depth", () => {
    let state = drillReducer(
      undefined,
      openDrill({ selection: billingSelection })
    );
    state = drillReducer(
      state,
      pushLevel({
        kind: "calls",
        selection: billingSelection,
        offset: 0,
      })
    );
    state = drillReducer(
      state,
      pushLevel({ kind: "transcript", conversationId: "abc-1" })
    );
    state = drillReducer(state, popToDepth(1));
    expect(state.stack).toHaveLength(1);
    expect(state.call).toBeUndefined();
    expect(state.calls).toBeUndefined();
  });

  it("setBucket flips the top-level bucket and invalidates timeseries cache", () => {
    let state = drillReducer(
      undefined,
      openDrill({ selection: billingSelection, bucket: "week" })
    );
    state = {
      ...state,
      timeseries: [
        {
          bucket_start: "2024-12-02",
          calls: 1,
          avg_sentiment_score: 0,
          satisfied_pct: 100,
          avg_handle_time_min: 5,
        },
      ],
    };
    state = drillReducer(state, setBucket("day"));
    const top = state.stack[0];
    if (top.kind === "timeseries") {
      expect(top.bucket).toBe("day");
    } else {
      throw new Error("expected timeseries");
    }
    expect(state.timeseries).toBeUndefined();
  });

  it("setTimeRange + setCallsOffset operate on the calls level", () => {
    let state = drillReducer(
      undefined,
      openDrill({ selection: billingSelection })
    );
    state = drillReducer(
      state,
      pushLevel({
        kind: "calls",
        selection: billingSelection,
        offset: 25,
      })
    );
    state = drillReducer(
      state,
      setTimeRange({ from: "2024-12-01T00:00:00Z", to: "2024-12-08T00:00:00Z" })
    );
    const calls = state.stack.find((l) => l.kind === "calls") as
      | (DrillLevel & { kind: "calls" })
      | undefined;
    expect(calls?.timeRange?.from).toBe("2024-12-01T00:00:00Z");
    // setTimeRange resets offset to 0.
    expect(calls?.offset).toBe(0);

    state = drillReducer(state, setCallsOffset(50));
    const calls2 = state.stack.find((l) => l.kind === "calls") as
      | (DrillLevel & { kind: "calls" })
      | undefined;
    expect(calls2?.offset).toBe(50);
  });

  it("setLoading + setError mirror request lifecycle", () => {
    let state = drillReducer(undefined, setLoading(true));
    expect(state.loading).toBe(true);
    state = drillReducer(state, setError("boom"));
    expect(state.loading).toBe(false);
    expect(state.error).toBe("boom");
  });

  it("closeDrill closes without clearing the stack; resetDrill clears everything", () => {
    let state = drillReducer(
      undefined,
      openDrill({ selection: billingSelection })
    );
    state = drillReducer(state, closeDrill());
    expect(state.isOpen).toBe(false);
    expect(state.stack).toHaveLength(1);

    state = drillReducer(state, resetDrill());
    expect(state.isOpen).toBe(false);
    expect(state.stack).toHaveLength(0);
  });

  it("restoreStack replaces the stack with the provided sequence", () => {
    const restored: DrillLevel[] = [
      { kind: "timeseries", selection: billingSelection, bucket: "week" },
      { kind: "calls", selection: billingSelection, offset: 0 },
    ];
    const state = drillReducer(undefined, restoreStack({ stack: restored }));
    expect(state.isOpen).toBe(true);
    expect(state.stack).toEqual(restored);
  });
});
