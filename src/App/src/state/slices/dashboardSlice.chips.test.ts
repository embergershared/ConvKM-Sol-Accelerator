import dashboardReducer, {
  addChip,
  clearChips,
  flattenChipsToSelectedFilters,
  removeChip,
  setChips,
  type ChartFilterChip,
} from "./dashboardSlice";

describe("dashboardSlice chips", () => {
  const topicChip: ChartFilterChip = {
    dimension: "Topic",
    value: "Billing",
    source: "chart",
  };
  const sentimentChip: ChartFilterChip = {
    dimension: "Sentiment",
    value: "Negative",
    source: "chart",
  };
  const manualChip: ChartFilterChip = {
    dimension: "Topic",
    value: "Lost or Stolen",
    source: "manual",
  };

  it("addChip appends a unique chip", () => {
    let state = dashboardReducer(undefined, addChip(topicChip));
    expect(state.chartFilterChips).toHaveLength(1);
    state = dashboardReducer(state, addChip(sentimentChip));
    expect(state.chartFilterChips).toHaveLength(2);
  });

  it("addChip deduplicates on (dimension, value)", () => {
    let state = dashboardReducer(undefined, addChip(topicChip));
    state = dashboardReducer(state, addChip(topicChip));
    expect(state.chartFilterChips).toHaveLength(1);
  });

  it("removeChip drops only the matching chip", () => {
    let state = dashboardReducer(undefined, addChip(topicChip));
    state = dashboardReducer(state, addChip(sentimentChip));
    state = dashboardReducer(
      state,
      removeChip({ dimension: "Topic", value: "Billing" })
    );
    expect(state.chartFilterChips).toHaveLength(1);
    expect(state.chartFilterChips[0].dimension).toBe("Sentiment");
  });

  it("clearChips() with no arg wipes all", () => {
    let state = dashboardReducer(undefined, addChip(topicChip));
    state = dashboardReducer(state, addChip(sentimentChip));
    state = dashboardReducer(state, clearChips());
    expect(state.chartFilterChips).toEqual([]);
  });

  it("clearChips('chart') leaves manual chips alone", () => {
    let state = dashboardReducer(undefined, addChip(topicChip));
    state = dashboardReducer(state, addChip(manualChip));
    state = dashboardReducer(state, clearChips("chart"));
    expect(state.chartFilterChips).toHaveLength(1);
    expect(state.chartFilterChips[0].source).toBe("manual");
  });

  it("setChips replaces the array wholesale", () => {
    let state = dashboardReducer(undefined, addChip(topicChip));
    state = dashboardReducer(state, setChips([sentimentChip]));
    expect(state.chartFilterChips).toEqual([sentimentChip]);
  });
});

describe("flattenChipsToSelectedFilters", () => {
  const topicChip: ChartFilterChip = {
    dimension: "Topic",
    value: "Billing",
    source: "chart",
  };
  const sentimentChip: ChartFilterChip = {
    dimension: "Sentiment",
    value: "Negative",
    source: "chart",
  };

  it("merges into an empty base", () => {
    const out = flattenChipsToSelectedFilters([topicChip, sentimentChip]);
    expect(out).toEqual({ Topic: ["Billing"], Sentiment: ["Negative"] });
  });

  it("dedupes when the chip value already exists in the base array", () => {
    const out = flattenChipsToSelectedFilters([topicChip], {
      Topic: ["Billing", "Other"],
    });
    expect(out.Topic).toEqual(["Billing", "Other"]);
  });

  it("appends a new value when the base array already has different values", () => {
    const out = flattenChipsToSelectedFilters([topicChip], { Topic: ["Other"] });
    expect(out.Topic).toEqual(["Other", "Billing"]);
  });

  it("upgrades a string base value to an array when the chip adds a second value", () => {
    const out = flattenChipsToSelectedFilters([topicChip], {
      Topic: "Other",
    });
    expect(out.Topic).toEqual(["Other", "Billing"]);
  });

  it("preserves unrelated base keys verbatim", () => {
    const out = flattenChipsToSelectedFilters([topicChip], {
      DateRange: ["Year to Date"],
    });
    expect(out.DateRange).toEqual(["Year to Date"]);
    expect(out.Topic).toEqual(["Billing"]);
  });

  it("drops the Sentiment 'all' sentinel when a real sentiment chip is added", () => {
    // Reproduces the bug where Sentiment: ["all", "Negative"] used to reach
    // Chart.tsx's getChartData, which empties Sentiment entirely when [0] is
    // "all" — so the chip's Negative was silently lost.
    const sentimentChip: ChartFilterChip = {
      dimension: "Sentiment",
      value: "Negative",
      source: "chart",
    };
    const out = flattenChipsToSelectedFilters([sentimentChip], {
      Sentiment: ["all"],
    });
    expect(out.Sentiment).toEqual(["Negative"]);
    expect(out.Sentiment).not.toContain("all");
  });

  it("strips stray 'all' from a mixed Sentiment array when appending a new value", () => {
    const sentimentChip: ChartFilterChip = {
      dimension: "Sentiment",
      value: "Neutral",
      source: "chart",
    };
    const out = flattenChipsToSelectedFilters([sentimentChip], {
      Sentiment: ["all", "Negative"],
    });
    expect(out.Sentiment).toEqual(["Negative", "Neutral"]);
  });
});
