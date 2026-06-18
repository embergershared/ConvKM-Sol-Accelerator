import React, { useCallback, useMemo } from "react";
import {
  Tag,
  TagGroup,
  Button,
  Caption1,
} from "@fluentui/react-components";
import {
  ChartMultipleRegular,
  DismissRegular,
} from "@fluentui/react-icons";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import {
  clearChips,
  removeChip,
  type ChartFilterChip,
} from "../../state/slices/dashboardSlice";
import { trackDrillEvent } from "../../utils/drillTelemetry";

export type SelectionPillBarProps = {
  /**
   * Called whenever a chip is removed or "Reset all" is clicked, so the parent
   * can re-fetch chart data with the updated chip set. The parent owns the
   * applyFilters fan-out; this component only mutates the chip array.
   */
  onChipsChanged?: () => void;
};

function chipKey(c: ChartFilterChip): string {
  return `${c.dimension}:${c.value}:${c.source}`;
}

const SelectionPillBar: React.FC<SelectionPillBarProps> = ({
  onChipsChanged,
}) => {
  const dispatch = useAppDispatch();
  const chips = useAppSelector((s) => s.dashboards.chartFilterChips);

  // Order: manual chips first, chart-origin chips second (per design plan).
  const orderedChips = useMemo(() => {
    const manual = chips.filter((c) => c.source === "manual");
    const chart = chips.filter((c) => c.source === "chart");
    return [...manual, ...chart];
  }, [chips]);

  const onDismiss = useCallback(
    (
      _e: unknown,
      data: { value: string; dismissedValue?: string }
    ) => {
      const found = orderedChips.find((c) => chipKey(c) === data.value);
      if (!found) return;
      dispatch(removeChip({ dimension: found.dimension, value: found.value }));
      trackDrillEvent("CrossFilterRemoved", {
        dimension: found.dimension,
        value: found.value,
        source: found.source,
      });
      onChipsChanged?.();
    },
    [dispatch, onChipsChanged, orderedChips]
  );

  const onResetAll = useCallback(() => {
    dispatch(clearChips());
    trackDrillEvent("CrossFilterRemoved", { value: "__all__" });
    onChipsChanged?.();
  }, [dispatch, onChipsChanged]);

  if (orderedChips.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Active dashboard selections"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        flexWrap: "wrap",
        padding: "6px 8px",
        background: "#fafafa",
        border: "1px solid #ececec",
        borderRadius: 4,
        marginBottom: 8,
      }}
    >
      <Caption1 style={{ color: "#555" }}>Selections:</Caption1>
      <TagGroup onDismiss={onDismiss} aria-label="Selection chips">
        {orderedChips.map((c) => (
          <Tag
            key={chipKey(c)}
            value={chipKey(c)}
            dismissible
            icon={c.source === "chart" ? <ChartMultipleRegular /> : undefined}
            shape="rounded"
            appearance={c.source === "chart" ? "brand" : "outline"}
            title={`${c.dimension}: ${c.value} (${c.source})`}
          >
            {c.dimension}: {c.value}
          </Tag>
        ))}
      </TagGroup>
      <Button
        size="small"
        appearance="subtle"
        icon={<DismissRegular />}
        onClick={onResetAll}
      >
        Reset all
      </Button>
    </div>
  );
};

export default SelectionPillBar;
