import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchChartData,
  fetchChartDataWithFilters,
  fetchFilterData,
} from "../../api/api";
import NoData from "../NoData/NoData";
import DonutChart from "../../chartComponents/DonutChart";
import BarChart from "../../chartComponents/HorizontalBarChart";
import WordCloudChart from "../../chartComponents/WordCloudChart";
import TopicTable from "../../chartComponents/TopicTable";
import Card from "../../chartComponents/Card";
import ChartFilter from "../ChartFilter/ChartFilter";
import SelectionPillBar from "../ChartFilter/SelectionPillBar";

import "./Chart.css";
import {
  type ChartConfigItem,
  type FilterMetaData,
  type SelectedFilters,
} from "../../types/AppTypes";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import {
  addChip,
  flattenChipsToSelectedFilters,
  setChartsData,
  setFetchingCharts,
  setFetchingFilters,
  setFiltersMeta,
  setFiltersMetaFetched,
  setInitialChartsDataFetched,
  type ChartFilterChip,
} from "../../state/slices/dashboardSlice";
import { openDrill } from "../../state/slices/drillSlice";
import { trackDrillEvent } from "../../utils/drillTelemetry";
import {
  ACCEPT_FILTERS,
  defaultSelectedFilters,
  getGridStyles,
} from "../../configs/Utils";
import { Button, Subtitle2, Tag } from "@fluentui/react-components";
import { OpenRegular } from "@fluentui/react-icons";
import { Spinner, SpinnerSize } from "@fluentui/react";
import { getSentimentColor } from "../../utils/chartUtils";

type ChartProps = {
  layoutWidthUpdated: boolean;
};

const Chart = ({ layoutWidthUpdated }: ChartProps) => {
  const dispatch = useAppDispatch();
  const charts = useAppSelector((state) => state.dashboards.charts);
  const fetchingCharts = useAppSelector(
    (state) => state.dashboards.fetchingCharts
  );
  const fetchingFilters = useAppSelector(
    (state) => state.dashboards.fetchingFilters
  );
  const filtersMetaFetched = useAppSelector(
    (state) => state.dashboards.filtersMetaFetched
  );
  const initialChartsDataFetched = useAppSelector(
    (state) => state.dashboards.initialChartsDataFetched
  );
  const configCharts = useAppSelector((state) => state.app.config.charts);

  const chartFilterChips = useAppSelector(
    (state) => state.dashboards.chartFilterChips
  );
  const dashboardSelectedFilters = useAppSelector(
    (state) => state.dashboards.selectedFilters
  );

  const [appliedFetch, setAppliedFetch] = useState<boolean>(false);
  const [widgetsGapInPercentage] = useState<number>(1);
  const fallbackChartWidthInPixels = 300;
  const [, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  const handleResize = useCallback(() => {
    setWindowSize({
      width: window.innerWidth,
      height: window.innerHeight,
    });
  }, []);

  useEffect(() => {
    requestAnimationFrame(() => {
      setTimeout(() => {
        setWindowSize({
          width: window.innerWidth,
          height: window.innerHeight,
        });
      }, 10);
    });
  }, [layoutWidthUpdated]);

  useEffect(() => {
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [handleResize]);

  const getChartData = useCallback(
    async (requestBody?: SelectedFilters) => {
      dispatch(setFetchingCharts(true));
      const normalizedRequestBody = requestBody
        ? { ...requestBody }
        : undefined;

      if (
        String((normalizedRequestBody as any)?.Sentiment?.[0]).toLowerCase() ===
        "all"
      ) {
        (normalizedRequestBody as any).Sentiment = [];
      }

      try {
        const chartData = normalizedRequestBody
          ? await fetchChartDataWithFilters({
              selected_filters: normalizedRequestBody,
            })
          : await fetchChartData();

        const updatedCharts: ChartConfigItem[] = configCharts
          .map((configChart: any) => {
            if (!configChart?.id) {
              return null;
            }

            const apiData = chartData.find(
              (apiChart: any) =>
                apiChart.id?.toLowerCase() === configChart.id?.toLowerCase()
            );

            const configObject: ChartConfigItem = {
              id: configChart.id,
              domId: configChart.id.replace(/\s+/g, "_").toUpperCase(),
              type: configChart.type,
              title: apiData ? apiData.chart_name : configChart.name || "",
              data: apiData ? apiData.chart_value : [],
              layout: {
                row: configChart.layout?.row,
                col: configChart.layout?.column,
                ...configChart.layout,
              },
            };

            if (configChart.layout?.width) {
              configObject.layout.width = configChart.layout.width;
            }

            return configObject;
          })
          .filter((chart): chart is ChartConfigItem => chart !== null);

        dispatch(setChartsData(updatedCharts));
      } catch {
        dispatch(setChartsData([]));
      } finally {
        dispatch(setFetchingCharts(false));
      }
    },
    [configCharts, dispatch]
  );

  useEffect(() => {
    const loadData = async () => {
      try {
        if (!filtersMetaFetched) {
          dispatch(setFetchingFilters(true));
          const filterResponse = await fetchFilterData();
          const acceptedFilters: FilterMetaData = {};

          filterResponse?.forEach((filter: any) => {
            if (ACCEPT_FILTERS.includes(filter?.filter_name)) {
              acceptedFilters[filter.filter_name] = filter.filter_values;
            }
          });

          dispatch(setFiltersMeta(acceptedFilters));
          dispatch(setFiltersMetaFetched(true));
          dispatch(setFetchingFilters(false));
        }

        if (!initialChartsDataFetched) {
          await getChartData({ ...defaultSelectedFilters });
          dispatch(setInitialChartsDataFetched(true));
        }
      } catch {
        dispatch(setChartsData([]));
        dispatch(setFetchingFilters(false));
      }
    };

    if (configCharts.length > 0) {
      void loadData();
    }
  }, [
    configCharts.length,
    dispatch,
    filtersMetaFetched,
    getChartData,
    initialChartsDataFetched,
  ]);

  const applyFilters = useCallback(
    async (updatedFilters: SelectedFilters) => {
      setAppliedFetch(true);
      await getChartData(updatedFilters);
      setAppliedFetch(false);
    },
    [getChartData]
  );

  // Stage C — cross-filter chips drive a re-fetch identical to the manual
  // ChartFilter "Apply" button path. We merge chips into the existing global
  // selectedFilters and dispatch through the same applyFilters callback so
  // the backend payload shape stays unchanged. Stringify the chip array for
  // useEffect's dep list to dodge identity-thrash on every render.
  const chipsKey = useMemo(
    () => JSON.stringify(chartFilterChips),
    [chartFilterChips]
  );
  useEffect(() => {
    if (!initialChartsDataFetched) return;
    const merged = flattenChipsToSelectedFilters(
      chartFilterChips,
      dashboardSelectedFilters
    );
    void applyFilters(merged);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chipsKey]);

  // Apply a cross-filter chip from a chart click. Dimension is the BACKEND
  // filter key ("Topic" | "Sentiment"); for "key_phrase" we don't have a
  // backend filter so the donut/bar/table call this and the word cloud
  // keeps its Stage B drill behavior. See Resolved decisions §4.
  const onCrossFilter = useCallback(
    (chip: ChartFilterChip, chartLabel: string) => {
      dispatch(addChip(chip));
      trackDrillEvent("CrossFilterApplied", {
        dimension: chip.dimension,
        value: chip.value,
        source: chip.source,
        chart: chartLabel,
      });
    },
    [dispatch]
  );

  // Investigate button — opens the drill drawer scoped to the chart's
  // highest-value mark. The frontend chart data is already sorted, so the
  // first entry is the top item for bars / tables / words; for the donut
  // we pick the slice with the largest value explicitly.
  const onInvestigate = useCallback(
    (chart: ChartConfigItem) => {
      if (!chart.data || chart.data.length === 0) return;
      let dimension: "topic" | "sentiment" | "key_phrase" = "topic";
      let value = "";
      if (chart.type === "donutchart") {
        dimension = "sentiment";
        const top = [...chart.data].sort(
          (a, b) => (parseInt(b.value) || 0) - (parseInt(a.value) || 0)
        )[0];
        value = top?.name ?? "";
      } else if (chart.type === "bar") {
        dimension = "topic";
        value = chart.data[0]?.name ?? "";
      } else if (chart.type === "table") {
        dimension = "topic";
        value = (chart.data[0]?.name as string) ?? "";
      } else if (chart.type === "wordcloud") {
        dimension = "key_phrase";
        const top = [...chart.data].sort(
          (a, b) => (b.size ?? 0) - (a.size ?? 0)
        )[0];
        value = top?.text ?? "";
      }
      if (!value) return;
      dispatch(openDrill({ selection: { dimension, value }, bucket: "week" }));
      trackDrillEvent("InvestigateClicked", {
        dimension,
        value,
        chart: chart.title,
      });
    },
    [dispatch]
  );

  const renderChart = (chart: ChartConfigItem, heightInPixels: number) => {
    const hasData = chart.data && chart.data.length > 0;

    switch (chart.type) {
      case "card":
        return hasData ? (
          <Card
            value={chart.data?.[0]?.value || "0"}
            description={chart.data?.[0]?.name || ""}
            unit_of_measurement={chart.data?.[0]?.unit_of_measurement || ""}
            containerHeight={heightInPixels}
          />
        ) : (
          <NoData />
        );
      case "donutchart":
        return hasData ? (
          <DonutChart
            title={chart.title}
            data={chart.data.map((item) => ({
              label: item.name,
              value: parseInt(item.value) || 0,
              color: getSentimentColor(item.name.toLowerCase()),
            }))}
            containerHeight={heightInPixels}
            widthInPixels={
              document.getElementById(chart.domId)?.clientWidth ??
              fallbackChartWidthInPixels
            }
            containerID={chart.domId}
            onSliceClick={(label) =>
              onCrossFilter(
                { dimension: "Sentiment", value: label, source: "chart" },
                chart.title
              )
            }
          />
        ) : (
          <div
            className="outerNoDataContainer"
            style={{
              height: `calc(${heightInPixels}px - 40px)`,
            }}
          >
            <NoData />
          </div>
        );
      case "bar":
        return hasData ? (
          <BarChart
            title={chart.title}
            data={chart.data.map((item) => ({
              category: item.name,
              value: parseFloat(item.value),
            }))}
            containerHeight={heightInPixels}
            containerID={chart.domId}
            onBarClick={(category) =>
              onCrossFilter(
                { dimension: "Topic", value: category, source: "chart" },
                chart.title
              )
            }
          />
        ) : (
          <div
            className="outerNoDataContainer"
            style={{
              height: `calc(${heightInPixels}px - 40px)`,
            }}
          >
            <NoData />
          </div>
        );
      case "table":
        return hasData ? (
          <TopicTable
            columns={["Topic", "Frequency", "Sentiment"]}
            columnKeys={["name", "call_frequency", "average_sentiment"]}
            rows={chart.data.map((item) => ({
              name: item.name,
              call_frequency: item.call_frequency,
              average_sentiment: item.average_sentiment,
            }))}
            containerHeight={heightInPixels}
            onRowClick={(row) => {
              const value = String(row["name"] ?? "");
              if (!value) return;
              onCrossFilter(
                { dimension: "Topic", value, source: "chart" },
                chart.title
              );
            }}
          />
        ) : (
          <div
            className="outerNoDataContainer"
            style={{
              height: `calc(${heightInPixels}px - 40px)`,
            }}
          >
            <NoData />
          </div>
        );
      case "wordcloud":
        return hasData ? (
          <WordCloudChart
            title={chart.title}
            data={{
              words: chart.data.map((item) => ({
                text: item.text,
                size: item.size,
                average_sentiment: item.average_sentiment,
              })),
            }}
            widthInPixels={
              document.getElementById(chart.domId)?.clientWidth ??
              fallbackChartWidthInPixels
            }
            containerHeight={heightInPixels}
            onWordClick={(text) => {
              // Stage C special-case: key_phrase isn't a backend filter yet, so
              // word-cloud plain click keeps Stage B drill behavior. Use the
              // Investigate button on this tile for parity with the other
              // charts. Documented in Resolved decisions §4.
              dispatch(
                openDrill({
                  selection: { dimension: "key_phrase", value: text },
                  bucket: "week",
                })
              );
              trackDrillEvent("DrillOpened", {
                dimension: "key_phrase",
                value: text,
                level: "timeseries",
                bucket: "week",
                source: "chart",
              });
            }}
          />
        ) : (
          <div
            className="outerNoDataContainer"
            style={{
              height: `calc(${heightInPixels}px - 40px)`,
            }}
          >
            <NoData />
          </div>
        );
      default:
        return null;
    }
  };

  const getHeightInPixels = (vh: number) => (vh / 100) * window.innerHeight;

  const groupedByRows: Record<string, ChartConfigItem[]> = {};
  charts.forEach((chart) => {
    const rowValue = String(chart.layout?.row);
    if (!groupedByRows[rowValue]) {
      groupedByRows[rowValue] = [];
    }
    groupedByRows[rowValue].push(chart);
  });

  const showAIGeneratedContentMessage =
    (!fetchingCharts && !fetchingFilters) || appliedFetch;

  return (
    <>
      {fetchingCharts && !appliedFetch ? (
        <div className="chartsLoaderContainer">
          <Spinner size={SpinnerSize.small} aria-label="Fetching Charts data" />
          <div className="loaderText">Loading Please wait...</div>
        </div>
      ) : (
        <div
          className="all-widgets-container"
          style={{
            filter: `blur(${fetchingCharts && appliedFetch ? "1.5px" : "0px"})`,
          }}
        >
          <SelectionPillBar />
          {Object.values(groupedByRows).map((chartsList, index) => {
            const gridStyles = getGridStyles(
              [...chartsList],
              widgetsGapInPercentage
            );
            let heightInPixels = 240;

            if (
              gridStyles.gridTemplateRows &&
              !Number.isNaN(parseInt(gridStyles.gridTemplateRows))
            ) {
              const heightInVH = parseInt(gridStyles.gridTemplateRows);
              heightInPixels = getHeightInPixels(heightInVH);
            }

            return (
              <div
                key={index}
                className="chart-container"
                style={{ ...gridStyles, gridGap: `${widgetsGapInPercentage}%` }}
              >
                {chartsList
                  .sort((a, b) => a.layout.col - b.layout.col)
                  .map((chart) => (
                    <div
                      key={chart.title}
                      id={chart.domId}
                      className={`chart-item ${chart.type}Container`}
                    >
                      <div className="chart-item-header">
                        <Subtitle2 className="chart-title">
                          {chart.title}
                        </Subtitle2>
                        {chart.type !== "card" && chart.data?.length > 0 && (
                          <Button
                            className="investigate-btn"
                            size="small"
                            appearance="subtle"
                            icon={<OpenRegular />}
                            aria-label={`Investigate ${chart.title}`}
                            title="Open drill drawer for the top item"
                            onClick={(e) => {
                              e.stopPropagation();
                              onInvestigate(chart);
                            }}
                          >
                            Investigate
                          </Button>
                        )}
                      </div>
                      {renderChart(chart, heightInPixels)}
                    </div>
                  ))}
              </div>
            );
          })}
        </div>
      )}

      {showAIGeneratedContentMessage && (
        <div style={{ textAlign: "center", gap: "2px" }}>
          <Tag size="extra-small" shape="circular">
            AI-generated content may be incorrect
          </Tag>
        </div>
      )}
      {!fetchingFilters && (
        <ChartFilter
          applyFilters={applyFilters}
          acceptFilters={ACCEPT_FILTERS}
          fetchingCharts={fetchingCharts}
        />
      )}
    </>
  );
};

export default Chart;
