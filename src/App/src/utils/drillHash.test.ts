import { decodeDrillStack, encodeDrillStack } from "./drillHash";
import type { DrillLevel } from "../types/Drill";

describe("drillHash", () => {
  it("encodes and decodes a single timeseries level", () => {
    const stack: DrillLevel[] = [
      {
        kind: "timeseries",
        selection: { dimension: "topic", value: "Billing" },
        bucket: "week",
      },
    ];
    const hash = encodeDrillStack(stack);
    expect(hash.startsWith("#/drill/")).toBe(true);
    const decoded = decodeDrillStack(hash);
    expect(decoded).toEqual(stack);
  });

  it("round-trips a calls level with time range", () => {
    const stack: DrillLevel[] = [
      {
        kind: "timeseries",
        selection: { dimension: "topic", value: "Billing" },
        bucket: "week",
      },
      {
        kind: "calls",
        selection: { dimension: "topic", value: "Billing" },
        timeRange: {
          from: "2024-12-01T00:00:00.000Z",
          to: "2024-12-08T00:00:00.000Z",
        },
        offset: 0,
      },
    ];
    const decoded = decodeDrillStack(encodeDrillStack(stack));
    expect(decoded).not.toBeNull();
    expect(decoded![1].kind).toBe("calls");
    if (decoded![1].kind === "calls") {
      expect(decoded![1].timeRange?.from).toBe("2024-12-01T00:00:00.000Z");
      expect(decoded![1].timeRange?.to).toBe("2024-12-08T00:00:00.000Z");
    }
  });

  it("round-trips a transcript level", () => {
    const stack: DrillLevel[] = [
      {
        kind: "timeseries",
        selection: { dimension: "key_phrase", value: "lost phone" },
        bucket: "day",
      },
      { kind: "transcript", conversationId: "abc-1" },
    ];
    const decoded = decodeDrillStack(encodeDrillStack(stack));
    expect(decoded).not.toBeNull();
    const top = decoded![decoded!.length - 1];
    expect(top.kind).toBe("transcript");
    if (top.kind === "transcript") expect(top.conversationId).toBe("abc-1");
  });

  it("returns null for non-drill hashes", () => {
    expect(decodeDrillStack("")).toBeNull();
    expect(decodeDrillStack("#/admin")).toBeNull();
    expect(decodeDrillStack("#some-anchor")).toBeNull();
  });

  it("returns null when no recognized dimension key is present", () => {
    expect(decodeDrillStack("#/drill/bucket=week")).toBeNull();
  });

  it("defaults bucket to week when missing or unrecognized", () => {
    const decoded = decodeDrillStack("#/drill/topic=Billing&bucket=fortnight");
    expect(decoded).not.toBeNull();
    const top = decoded![0];
    if (top.kind === "timeseries") expect(top.bucket).toBe("week");
  });
});
