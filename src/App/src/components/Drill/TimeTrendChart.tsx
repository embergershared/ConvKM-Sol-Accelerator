import React, { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import { fetchDrillTimeseries } from "../../api/api";
import {
  pushLevel,
  setBucket,
  setError,
  setLoading,
  setTimeseries,
} from "../../state/slices/drillSlice";
import {
  Body1,
  RadioGroup,
  Radio,
  Spinner,
  Subtitle2,
} from "@fluentui/react-components";
import type { DrillBucket, TimeseriesPoint } from "../../types/Drill";
import "./drill.css";

const dayMs = 24 * 60 * 60 * 1000;
const weekMs = 7 * dayMs;

function bucketRangeFromStart(start: string, bucket: DrillBucket) {
  const from = new Date(start);
  const to = new Date(from.getTime() + (bucket === "week" ? weekMs : dayMs));
  return {
    from: from.toISOString(),
    to: to.toISOString(),
  };
}

const TimeTrendChart: React.FC = () => {
  const dispatch = useAppDispatch();
  const stack = useAppSelector((s) => s.drill.stack);
  const timeseries = useAppSelector((s) => s.drill.timeseries);
  const loading = useAppSelector((s) => s.drill.loading);
  const error = useAppSelector((s) => s.drill.error);
  const globalFilters = useAppSelector((s) => s.dashboards.selectedFilters);

  const svgRef = useRef<SVGSVGElement | null>(null);

  const top = stack[0];
  const level = top && top.kind === "timeseries" ? top : null;
  const filtersKey = JSON.stringify(globalFilters);

  useEffect(() => {
    if (!level) return;
    let cancelled = false;
    (async () => {
      dispatch(setLoading(true));
      try {
        const data = await fetchDrillTimeseries({
          selection: level.selection,
          bucket: level.bucket,
          filters: { selected_filters: globalFilters as any },
        });
        if (!cancelled) dispatch(setTimeseries(data));
      } catch (e: any) {
        if (!cancelled)
          dispatch(setError(e?.message ?? "Failed to load timeseries"));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    dispatch,
    level?.selection.dimension,
    level?.selection.value,
    level?.bucket,
    filtersKey,
  ]);

  const data: TimeseriesPoint[] = useMemo(() => timeseries ?? [], [timeseries]);

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    // Reuse the singleton tooltip pattern from HorizontalBarChart.tsx — one
    // tooltip per page, removed on re-render to avoid stale handlers.
    d3.selectAll("#drill-tooltip-container").remove();

    if (!data.length) return;

    const margin = { top: 16, right: 56, bottom: 36, left: 56 };
    const width = svgEl.clientWidth || 480;
    const height = 280;
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const g = svg
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3
      .scaleBand<string>()
      .domain(data.map((d) => d.bucket_start))
      .range([0, innerW])
      .padding(0.2);

    const yLeft = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.calls) ?? 1])
      .nice()
      .range([innerH, 0]);

    const yRight = d3.scaleLinear().domain([-1, 1]).range([innerH, 0]);

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(
        d3
          .axisBottom(x)
          .tickValues(
            x.domain().filter((_, i, arr) => i % Math.ceil(arr.length / 6) === 0)
          )
          .tickFormat((d) => new Date(d as string).toLocaleDateString())
      )
      .selectAll("text")
      .style("font-size", "10px");

    g.append("g")
      .call(d3.axisLeft(yLeft).ticks(5))
      .selectAll("text")
      .style("font-size", "10px");
    g.append("g")
      .attr("transform", `translate(${innerW},0)`)
      .call(d3.axisRight(yRight).ticks(5))
      .selectAll("text")
      .style("font-size", "10px");

    // Axis labels — call volume on the left, sentiment on the right.
    g.append("text")
      .attr("transform", `translate(${-margin.left + 14}, ${innerH / 2}) rotate(-90)`)
      .style("text-anchor", "middle")
      .style("font-size", "11px")
      .style("fill", "#0078d4")
      .text("Calls");

    g.append("text")
      .attr(
        "transform",
        `translate(${innerW + margin.right - 14}, ${innerH / 2}) rotate(-90)`
      )
      .style("text-anchor", "middle")
      .style("font-size", "11px")
      .style("fill", "#107c10")
      .text("Avg sentiment (-1 to +1)");

    // Shared tooltip container — appended to body so it can escape svg/drawer
    // overflow clipping.
    const tooltip = d3
      .select("body")
      .append("div")
      .attr("id", "drill-tooltip-container")
      .style("position", "absolute")
      .style("background", "#fff")
      .style("padding", "8px 10px")
      .style("border", "1px solid #ccc")
      .style("border-radius", "4px")
      .style("font-size", "12px")
      .style("box-shadow", "0px 2px 6px rgba(0,0,0,0.15)")
      .style("pointer-events", "none")
      .style("display", "none")
      .style("z-index", "10000");

    const formatTooltip = (d: TimeseriesPoint) => {
      const score = Number.isFinite(d.avg_sentiment_score)
        ? d.avg_sentiment_score.toFixed(2)
        : "—";
      const satisfied = Number.isFinite(d.satisfied_pct)
        ? `${d.satisfied_pct.toFixed(0)}%`
        : "—";
      const aht = Number.isFinite(d.avg_handle_time_min)
        ? `${d.avg_handle_time_min.toFixed(1)} min`
        : "—";
      return (
        `<strong>${new Date(d.bucket_start).toLocaleDateString()}</strong><br>` +
        `Calls: <strong>${d.calls}</strong><br>` +
        `Avg sentiment: <strong>${score}</strong><br>` +
        `Satisfied: <strong>${satisfied}</strong><br>` +
        `Avg handle time: <strong>${aht}</strong>`
      );
    };

    const onPickBucket = (d: TimeseriesPoint) => {
      if (!level) return;
      const range = bucketRangeFromStart(d.bucket_start, level.bucket);
      dispatch(
        pushLevel({
          kind: "calls",
          selection: level.selection,
          timeRange: range,
          offset: 0,
        })
      );
    };

    g.selectAll(".bar")
      .data(data)
      .enter()
      .append("rect")
      .attr("class", "bar drill-mark")
      .attr("x", (d) => x(d.bucket_start) ?? 0)
      .attr("y", (d) => yLeft(d.calls))
      .attr("width", x.bandwidth())
      .attr("height", (d) => innerH - yLeft(d.calls))
      .attr("fill", "#0078d4")
      .attr("rx", 3)
      .attr("role", "button")
      .attr("tabindex", 0)
      .attr(
        "aria-label",
        (d) =>
          `${d.calls} calls in bucket starting ${d.bucket_start}. Press Enter to drill into call list.`
      )
      .on("mouseover", (_event, d) => {
        tooltip.style("display", "block").html(formatTooltip(d));
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", `${event.pageX + 12}px`)
          .style("top", `${event.pageY - 12}px`);
      })
      .on("mouseout", () => {
        tooltip.style("display", "none");
      })
      .on("click", (_, d) => onPickBucket(d))
      .on("keydown", (event, d) => {
        const ke = event as unknown as KeyboardEvent;
        if (ke.key === "Enter" || ke.key === " ") {
          ke.preventDefault();
          onPickBucket(d);
        }
      });

    const line = d3
      .line<TimeseriesPoint>()
      .x((d) => (x(d.bucket_start) ?? 0) + x.bandwidth() / 2)
      .y((d) => yRight(d.avg_sentiment_score))
      .curve(d3.curveMonotoneX);

    g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", "#107c10")
      .attr("stroke-width", 2)
      .attr("d", line);

    // Sentiment dots — give the line a hover target too, with the same tooltip.
    g.selectAll(".sent-dot")
      .data(data)
      .enter()
      .append("circle")
      .attr("class", "sent-dot")
      .attr("cx", (d) => (x(d.bucket_start) ?? 0) + x.bandwidth() / 2)
      .attr("cy", (d) => yRight(d.avg_sentiment_score))
      .attr("r", 3)
      .attr("fill", "#107c10")
      .style("pointer-events", "all")
      .on("mouseover", (_event, d) => {
        tooltip.style("display", "block").html(formatTooltip(d));
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", `${event.pageX + 12}px`)
          .style("top", `${event.pageY - 12}px`);
      })
      .on("mouseout", () => {
        tooltip.style("display", "none");
      });

    return () => {
      d3.selectAll("#drill-tooltip-container").remove();
    };
  }, [
    data,
    dispatch,
    level?.bucket,
    level?.selection.dimension,
    level?.selection.value,
    level,
  ]);

  if (!level) return null;

  return (
    <div>
      <div
        className="drill-bucket-toggle"
        style={{ justifyContent: "space-between" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Subtitle2>Bucket:</Subtitle2>
          <RadioGroup
            layout="horizontal"
            value={level.bucket}
            onChange={(_, data) =>
              dispatch(setBucket(data.value as DrillBucket))
            }
          >
            <Radio value="day" label="Day" />
            <Radio value="week" label="Week" />
          </RadioGroup>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span
              aria-hidden
              style={{
                width: 10,
                height: 10,
                background: "#0078d4",
                display: "inline-block",
                borderRadius: 2,
              }}
            />
            <Body1>Calls</Body1>
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span
              aria-hidden
              style={{
                width: 14,
                height: 2,
                background: "#107c10",
                display: "inline-block",
              }}
            />
            <Body1>Avg sentiment</Body1>
          </span>
        </div>
      </div>
      {loading && (
        <div className="drill-loading">
          <Spinner size="tiny" />
          <Body1>Loading trend…</Body1>
        </div>
      )}
      {error && <div className="drill-error">{error}</div>}
      {!loading && !error && data.length === 0 && (
        <div className="drill-empty">No data for this selection.</div>
      )}
      <svg ref={svgRef} className="drill-timetrend-svg" />
    </div>
  );
};

export default TimeTrendChart;
