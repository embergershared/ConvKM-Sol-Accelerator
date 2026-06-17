import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Stack,
  DefaultButton,
  DirectionalHint,
  IContextualMenuListProps,
  IContextualMenuItem,
  IRenderFunction,
  SearchBox,
  Icon,
  VerticalDivider,
} from "@fluentui/react";
import "./ChartFilter.css";
import { type SelectedFilters } from "../../types/AppTypes";
import { defaultSelectedFilters, sentimentIcons } from "../../configs/Utils";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import {
  setSelectedFilters as setSelectedDashboardFilters,
  addChip,
  clearChips,
} from "../../state/slices/dashboardSlice";
import {
  ArrowClockwise20Regular,
  CalendarLtr20Regular,
  ChatMultiple20Regular,
  Emoji20Regular,
  EmojiMeh20Regular,
  EmojiMultiple20Regular,
  EmojiSad20Regular,
  MicRegular,
} from "@fluentui/react-icons";
interface FilterComponentProps {
  applyFilters: (updatedFilters: SelectedFilters) => void;
  acceptFilters: string[];
  fetchingCharts: boolean;
}

const ChartFilter: React.FC<FilterComponentProps> = (props) => {
  const dispatch = useAppDispatch();
  const { selectedFilters, filtersMeta } = useAppSelector(
    (state) => state.dashboards
  );
  const { applyFilters, fetchingCharts } = props;
  const initialDateRange = Array.isArray(selectedFilters.DateRange)
    ? selectedFilters.DateRange
    : [""];

  const chartFilterChips = useAppSelector(
    (state) => state.dashboards.chartFilterChips
  );

  const [selectedDateRange, setSelectedDateRange] = useState<string[]>(
    initialDateRange as string[]
  );
  const [selectedCsat, setSelectedCsat] = useState<string[]>(
    selectedFilters.Sentiment as string[]
  );
  const [selectedTopics, setSelectedTopics] = useState<string[]>(
    selectedFilters.Topic as string[]
  );
  const [selectedRecording, setSelectedRecording] = useState<string[]>(
    (selectedFilters.Recording as string[]) || ["all"]
  );

  // Sync chips → local state: when a chip is removed/cleared from the
  // SelectionPillBar, reflect that removal in the bottom filter bar's local
  // state so both UIs stay consistent.
  useEffect(() => {
    const topicChipValues = chartFilterChips
      .filter((c) => c.dimension === "Topic")
      .map((c) => c.value);
    const sentimentChipValues = chartFilterChips
      .filter((c) => c.dimension === "Sentiment")
      .map((c) => c.value);

    // Sync topics: local state should match chip values (for chart-origin chips
    // these are additive; for manual chips they mirror what the user selected)
    setSelectedTopics(topicChipValues);

    // Sync sentiment: if a sentiment chip exists, select it; otherwise reset
    if (sentimentChipValues.length > 0) {
      setSelectedCsat(sentimentChipValues);
    } else {
      setSelectedCsat(defaultSelectedFilters.Sentiment as string[]);
    }
  }, [chartFilterChips]);

  const [isDateMenuOpen, setIsDateMenuOpen] = useState(false);
  const [isCsatMenuOpen, setIsCsatMenuOpen] = useState(false);
  const [isTopicsMenuOpen, setIsTopicsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredTopics = filtersMeta?.Topic?.filter((option) =>
    option.displayValue.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const onSearchChange = (
    ev: React.KeyboardEvent<HTMLInputElement>,
    newValue: string
  ) => {
    setSearchQuery(newValue || "");
  };

  const handleTopicSelection = (e: any, key: string) => {
    e.preventDefault();
    setSelectedTopics((prevSelected) =>
      prevSelected.includes(key)
        ? prevSelected.filter((topic) => topic !== key)
        : [...prevSelected, key]
    );
  };

  const handleDateSelection = (key: string) => {
    setSelectedDateRange([key]);
    setIsDateMenuOpen(false);
  };

  const handleCsatSelection = (key: string) => {
    setSelectedCsat([key]);
    setIsCsatMenuOpen(false);
  };

  const handleRecordingSelection = (key: string) => {
    setSelectedRecording([key]);
  };

  const handleApplyFilters = () => {
    const startDate = selectedDateRange || [""];
    const updatedFilters: SelectedFilters = {};
    updatedFilters.Topic = selectedTopics;
    updatedFilters.Sentiment = selectedCsat;
    updatedFilters.DateRange = startDate;
    updatedFilters.Recording = selectedRecording;
    applyFilters(updatedFilters);
    dispatch(setSelectedDashboardFilters(updatedFilters));

    // Sync local selections → chips so the SelectionPillBar reflects what the
    // user chose in the bottom filter bar. Clear previous manual chips first
    // to avoid stale entries, then re-add current selections.
    dispatch(clearChips("manual"));
    for (const topic of selectedTopics) {
      dispatch(addChip({ dimension: "Topic", value: topic, source: "manual" }));
    }
    const sentimentVal = selectedCsat?.[0];
    if (sentimentVal && sentimentVal.toLowerCase() !== "all") {
      dispatch(
        addChip({ dimension: "Sentiment", value: sentimentVal, source: "manual" })
      );
    }
  };

  const handleResetFilters = () => {
    setSelectedDateRange(defaultSelectedFilters.DateRange as string[]);
    setSelectedCsat(defaultSelectedFilters.Sentiment); // Assuming "all" is the key for the "all" sentiment
    setSelectedTopics(defaultSelectedFilters.Topic as []);
    setSelectedRecording(defaultSelectedFilters.Recording as string[]);
    // Clear all chips so the SelectionPillBar stays in sync
    dispatch(clearChips());
  };
  const getDisplayValue = (
    filterList: { key: string; displayValue: string }[],
    key: string
  ) => {
    const matched = filterList?.find(
      (ob: any) => String(ob?.key) === String(key)
    );
    if (matched?.displayValue) {
      return matched.displayValue as string;
    }
    return "";
  };

  const onTopicsMenuOpen = () => {
    setSearchQuery("");
    setTimeout(() => {
      const element = document.getElementById("SEARCH_TOPICS");
      if (element) {
        element.focus();
      }
    }, 100);
  };

  const handleDeselectAll = useCallback((ev: React.MouseEvent<HTMLElement>) => {
    ev.preventDefault();
    setSelectedTopics([]);
  }, []);

  const renderMenuList: IRenderFunction<IContextualMenuListProps> = useCallback(
    (menuListProps, defaultRender) => (
      <div>
        <button
          className="options resetTopicsButton"
          type="button"
          onClick={handleDeselectAll}
          disabled={selectedTopics.length === 0}
        >
          <div>
            <i aria-hidden="true" className="deselectIcon"></i>
            <span> Reset topics</span>
          </div>
        </button>
        <div style={{ borderBottom: "1px solid #ccc" }}></div>
        {defaultRender ? defaultRender(menuListProps) : null}
        <div style={{ borderBottom: "1px solid #ccc" }}> </div>
        <SearchBox
          className="searchTopics"
          ariaLabel="Filter topics"
          placeholder="Search topics"
          onClear={() => {
            setSearchQuery("");
          }}
          onKeyUp={(e) => {
            onSearchChange(e, (e.target as HTMLInputElement).value);
          }}
          iconProps={{ iconName: "Search" }}
          styles={{ root: { margin: "8px" } }}
          id="SEARCH_TOPICS"
          showIcon
          autoComplete="off"
          autoFocus
        />
      </div>
    ),
    [handleDeselectAll, selectedTopics.length]
  );

  const topicMenuProps = useMemo(
    () => ({
      onRenderMenuList: renderMenuList,
      items: filteredTopics.length
        ? (filteredTopics?.map((option) => ({
            key: option.key,
            text: option.displayValue,
            canCheck: true,
            shouldFocusOnMount: true,
            checked: selectedTopics.includes(option.key),
            onClick: (e) => handleTopicSelection(e, option.key),
          })) as IContextualMenuItem[])
        : ([
            {
              key: "no_results",
              onRender: () => (
                <div key="no_results" className="no-result">
                  <Icon iconName="SearchIssue" title="No result found" />
                  <span>No topics found</span>
                </div>
              ),
            },
          ] as IContextualMenuItem[]),
      directionalHint: DirectionalHint.bottomLeftEdge,
      onMenuOpened: () => onTopicsMenuOpen(),
    }),
    [filteredTopics, renderMenuList, selectedTopics]
  );

  return (
    <Stack
      horizontal
      tokens={{ childrenGap: 10 }}
      className="filters-container"
    >
      <div className="filterOuterContainer">
        <DefaultButton
          onRenderIcon={() => <CalendarLtr20Regular />}
          text={getDisplayValue(
            filtersMeta?.DateRange,
            selectedDateRange[0] || ""
          )}
          onClick={() => setIsDateMenuOpen(!isDateMenuOpen)}
          menuProps={{
            items: filtersMeta?.DateRange?.map((option) => ({
              key: String(option.key),
              text: option.displayValue,
              canCheck: true,
              checked: option.key === selectedDateRange[0],
              onClick: () => handleDateSelection(String(option.key)),
            })),
            calloutProps: {
              directionalHintFixed: true,
              styles: { calloutMain: { maxHeight: 300, overflowY: "auto" } },
            },
            directionalHint: DirectionalHint.topLeftEdge,
            onDismiss: () => setIsDateMenuOpen(false),
          }}
          disabled={fetchingCharts}
        />
        <VerticalDivider />
        <DefaultButton
          className="capitalize-text"
          onClick={() => setIsCsatMenuOpen(!isCsatMenuOpen)}
          menuProps={{
            styles: { root: { minWidth: "13rem" } },
            items: filtersMeta?.Sentiment?.map((option) => ({
              key: String(option.key),
              iconProps: {
                iconName:
                  sentimentIcons[option.key] || "EmojiMultiple20Regular",
              },
              onRenderIcon: (renderIconProps) => {
                switch (renderIconProps?.item.key) {
                  case "Positive":
                    return <Emoji20Regular />;
                  case "Neutral":
                    return <EmojiMeh20Regular />;
                  case "Negative":
                    return <EmojiSad20Regular />;
                  default:
                    return <EmojiMultiple20Regular />;
                }
              },
              text: option.displayValue,
              checked: option.key === selectedCsat?.[0],
              onClick: () => handleCsatSelection(String(option.key)),
            })),
            directionalHint: DirectionalHint.topLeftEdge,
            calloutProps: {
              directionalHintFixed: true,
              styles: { calloutMain: { maxHeight: 300, overflowY: "auto" } },
            },
            onDismiss: () => setIsCsatMenuOpen(false),
          }}
          disabled={fetchingCharts}
        >
          {(() => {
            switch (selectedCsat?.[0]) {
              case "Positive":
                return <Emoji20Regular />;
              case "Neutral":
                return <EmojiMeh20Regular />;
              case "Negative":
                return <EmojiSad20Regular />;
              default:
                return <EmojiMultiple20Regular />;
            }
          })()}
          {getDisplayValue(filtersMeta?.Sentiment, selectedCsat?.[0] || "")}
        </DefaultButton>
        <VerticalDivider />
        <DefaultButton
          onRenderIcon={() => <ChatMultiple20Regular />}
          text={`Topics (${selectedTopics?.length})`}
          onClick={() => setIsTopicsMenuOpen(!isTopicsMenuOpen)}
          disabled={fetchingCharts}
          menuProps={topicMenuProps}
        />
        <VerticalDivider />
        <DefaultButton
          onRenderIcon={() => <MicRegular />}
          text={
            selectedRecording?.[0] === "all"
              ? "Recording"
              : selectedRecording?.[0] || "Recording"
          }
          menuProps={{
            items: (filtersMeta?.Recording || [
              { key: "all", displayValue: "all" },
              { key: "With Recording", displayValue: "With Recording" },
              { key: "Without Recording", displayValue: "Without Recording" },
            ]).map((option) => ({
              key: String(option.key),
              text: option.displayValue === "all" ? "All" : option.displayValue,
              canCheck: true,
              checked: option.key === selectedRecording?.[0],
              onClick: () => handleRecordingSelection(String(option.key)),
            })),
            directionalHint: DirectionalHint.topLeftEdge,
            calloutProps: {
              directionalHintFixed: true,
              styles: { calloutMain: { maxHeight: 300, overflowY: "auto" } },
            },
          }}
          disabled={fetchingCharts}
        />
        <VerticalDivider />
        <DefaultButton
          onRenderIcon={() => <ArrowClockwise20Regular />}
          onClick={handleResetFilters}
          styles={{ root: { padding: "0px" } }}
          title="Reset"
          disabled={fetchingCharts}
        />
        <VerticalDivider />
        <DefaultButton
          className="applyBtn"
          onClick={handleApplyFilters}
          disabled={fetchingCharts}
        >
          Apply
        </DefaultButton>
      </div>
    </Stack>
  );
};

export default ChartFilter;
