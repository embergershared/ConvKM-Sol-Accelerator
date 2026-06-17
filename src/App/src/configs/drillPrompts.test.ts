import {
  buildPromptForStack,
  DRILL_PROMPT_TEMPLATES,
  format,
} from "./drillPrompts";
import type { DrillLevel } from "../types/Drill";

describe("drillPrompts.format", () => {
  it("substitutes simple placeholders", () => {
    expect(format("Hello {name}", { value: "ignored", from: "x" } as any)).toBe(
      "Hello unspecified"
    );
    expect(format("{value} from {from}", { value: "Billing", from: "2024-01-01" })).toBe(
      "Billing from 2024-01-01"
    );
  });

  it("replaces missing or empty values with 'unspecified' instead of leaking literals", () => {
    expect(format("{from} - {to}", { from: undefined, to: "" })).toBe(
      "unspecified - unspecified"
    );
  });

  it("leaves unknown placeholders as 'unspecified' (no literal leak)", () => {
    expect(format("hello {nonsense}", {})).toBe("hello unspecified");
  });

  it("short-formats ISO datetime fields (from/to) to YYYY-MM-DD", () => {
    expect(
      format("{from} - {to}", {
        from: "2024-12-01T00:00:00.000Z",
        to: "2024-12-08T13:45:22Z",
      })
    ).toBe("2024-12-01 - 2024-12-08");
  });
});

describe("drillPrompts registry coverage", () => {
  const dimensions = ["topic", "sentiment", "key_phrase"] as const;

  it("has a non-empty template for every (timeseries, dimension)", () => {
    const ts = DRILL_PROMPT_TEMPLATES.timeseries as Record<string, string>;
    for (const d of dimensions) {
      expect(typeof ts[d]).toBe("string");
      expect(ts[d].length).toBeGreaterThan(20);
    }
  });

  it("has a non-empty template for every (calls, dimension)", () => {
    const calls = DRILL_PROMPT_TEMPLATES.calls as Record<string, string>;
    for (const d of dimensions) {
      expect(typeof calls[d]).toBe("string");
      expect(calls[d].length).toBeGreaterThan(20);
    }
  });

  it("has a transcript template (string, used at L3 with inlined transcript text)", () => {
    expect(typeof DRILL_PROMPT_TEMPLATES.transcript).toBe("string");
    expect((DRILL_PROMPT_TEMPLATES.transcript as string).length).toBeGreaterThan(50);
  });
});

describe("buildPromptForStack", () => {
  const topicSelection = { dimension: "topic" as const, value: "Billing" };

  it("returns '' for an empty stack", () => {
    expect(buildPromptForStack([])).toBe("");
  });

  it("uses the timeseries template for an L1 stack and substitutes value", () => {
    const stack: DrillLevel[] = [
      { kind: "timeseries", selection: topicSelection, bucket: "week" },
    ];
    const out = buildPromptForStack(stack);
    expect(out).toContain("Billing");
    expect(out).not.toContain("{value}");
    expect(out).not.toContain("{bucket}");
  });

  it("uses the calls template for an L2 stack with short-formatted dates", () => {
    const stack: DrillLevel[] = [
      { kind: "timeseries", selection: topicSelection, bucket: "week" },
      {
        kind: "calls",
        selection: topicSelection,
        timeRange: {
          from: "2024-12-01T00:00:00.000Z",
          to: "2024-12-08T00:00:00.000Z",
        },
        offset: 0,
      },
    ];
    const out = buildPromptForStack(stack);
    expect(out).toContain("Billing");
    expect(out).toContain("2024-12-01");
    // ISO millis must NOT leak — the agent's date tools want short dates.
    expect(out).not.toContain("T00:00:00");
    expect(out).not.toMatch(/\{[a-z]+\}/);
  });

  it("inlines the full transcript text + conversation id at L3 when callDetail is provided", () => {
    const stack: DrillLevel[] = [
      { kind: "timeseries", selection: topicSelection, bucket: "week" },
      { kind: "calls", selection: topicSelection, offset: 0 },
      { kind: "transcript", conversationId: "abc-123" },
    ];
    const callDetail = {
      conversation_id: "abc-123",
      start_time: "2024-12-02T00:01:00",
      end_time: "2024-12-02T00:10:00",
      duration_min: 9,
      sentiment: "Negative",
      satisfied: "No",
      topic: "Billing",
      complaint: "wrong charge",
      key_phrases: ["billing", "charge"],
      summary: "Customer complained about a billing charge.",
      transcript_raw:
        "Hi, this is Alex. I think I was double-charged. Hello Alex, let me check that.",
    };
    const out = buildPromptForStack(stack, callDetail);
    expect(out).toContain("abc-123");
    expect(out).toContain("Hi, this is Alex");
    expect(out).toContain("double-charged");
    expect(out).not.toMatch(/\{[a-z]+\}/);
  });

  it("falls back to a generic per-topic prompt at L3 when callDetail is missing", () => {
    const stack: DrillLevel[] = [
      { kind: "timeseries", selection: topicSelection, bucket: "week" },
      { kind: "calls", selection: topicSelection, offset: 0 },
      { kind: "transcript", conversationId: "abc-123" },
    ];
    const out = buildPromptForStack(stack);
    // No transcript loaded yet — must NOT contain the unsubstituted placeholder.
    expect(out).not.toContain("{transcript}");
    expect(out).not.toContain("abc-123");
    // Should still mention the topic context so the prompt is useful.
    expect(out).toContain("Billing");
  });

  it("picks the deepest non-transcript selection when the top is a transcript", () => {
    const stack: DrillLevel[] = [
      { kind: "timeseries", selection: topicSelection, bucket: "week" },
      {
        kind: "calls",
        selection: { dimension: "key_phrase", value: "lost phone" },
        offset: 0,
      },
      { kind: "transcript", conversationId: "abc-1" },
    ];
    const out = buildPromptForStack(stack, {
      conversation_id: "abc-1",
      start_time: "x",
      end_time: "y",
      duration_min: 1,
      sentiment: "Positive",
      satisfied: "Yes",
      topic: "Lost Devices",
      complaint: null,
      key_phrases: [],
      summary: "s",
      transcript_raw: "Hello. I lost my phone.",
    });
    expect(out).toContain("Hello. I lost my phone.");
    expect(out).toContain("abc-1");
  });
});
