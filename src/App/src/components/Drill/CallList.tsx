import React, { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import { fetchDrillCalls } from "../../api/api";
import {
  pushLevel,
  setCalls,
  setCallsOffset,
  setError,
  setLoading,
} from "../../state/slices/drillSlice";
import {
  Body1,
  Button,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Tag,
} from "@fluentui/react-components";
import type { CallListItem, DrillLevel } from "../../types/Drill";
import "./drill.css";

const PAGE_SIZE = 25;

const CallList: React.FC = () => {
  const dispatch = useAppDispatch();
  const stack = useAppSelector((s) => s.drill.stack);
  const calls = useAppSelector((s) => s.drill.calls);
  const loading = useAppSelector((s) => s.drill.loading);
  const error = useAppSelector((s) => s.drill.error);
  const globalFilters = useAppSelector((s) => s.dashboards.selectedFilters);

  const level = stack.find((l) => l.kind === "calls") as
    | (DrillLevel & { kind: "calls" })
    | undefined;
  const filtersKey = JSON.stringify(globalFilters);

  useEffect(() => {
    if (!level) return;
    let cancelled = false;
    (async () => {
      dispatch(setLoading(true));
      try {
        const data = await fetchDrillCalls({
          selection: level.selection,
          time_range: level.timeRange,
          filters: { selected_filters: globalFilters as any },
          offset: level.offset,
          limit: PAGE_SIZE,
        });
        if (!cancelled) dispatch(setCalls(data));
      } catch (e: any) {
        if (!cancelled) dispatch(setError(e?.message ?? "Failed to load calls"));
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
    level?.timeRange?.from,
    level?.timeRange?.to,
    level?.offset,
    filtersKey,
  ]);

  if (!level) return null;

  const items: CallListItem[] = calls?.items ?? [];
  const total = calls?.total ?? 0;
  const page = Math.floor(level.offset / PAGE_SIZE) + 1;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const goToTranscript = (id: string) =>
    dispatch(pushLevel({ kind: "transcript", conversationId: id }));

  return (
    <div>
      {loading && (
        <div className="drill-loading">
          <Spinner size="tiny" />
          <Body1>Loading calls…</Body1>
        </div>
      )}
      {error && <div className="drill-error">{error}</div>}
      {!loading && !error && items.length === 0 && (
        <div className="drill-empty">No calls in this slice.</div>
      )}
      {!loading && !error && items.length > 0 && (
        <>
          <Body1 style={{ marginBottom: 8 }}>
            {total} call{total === 1 ? "" : "s"} · showing {level.offset + 1}–
            {Math.min(level.offset + items.length, total)}
          </Body1>
          <Table aria-label="Drill call list" size="small">
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Start</TableHeaderCell>
                <TableHeaderCell>Duration</TableHeaderCell>
                <TableHeaderCell>Sentiment</TableHeaderCell>
                <TableHeaderCell>Satisfied</TableHeaderCell>
                <TableHeaderCell>Topic</TableHeaderCell>
                <TableHeaderCell>Complaint</TableHeaderCell>
                <TableHeaderCell>Summary</TableHeaderCell>
                <TableHeaderCell></TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow
                  key={item.conversation_id}
                  role="button"
                  tabIndex={0}
                  onClick={() => goToTranscript(item.conversation_id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      goToTranscript(item.conversation_id);
                    }
                  }}
                  style={{ cursor: "pointer" }}
                >
                  <TableCell>
                    {new Date(item.start_time).toLocaleString()}
                  </TableCell>
                  <TableCell>{item.duration_min} min</TableCell>
                  <TableCell>
                    <Tag size="small" appearance="outline">
                      {item.sentiment}
                    </Tag>
                  </TableCell>
                  <TableCell>{item.satisfied}</TableCell>
                  <TableCell>{item.topic}</TableCell>
                  <TableCell>
                    {item.complaint ? (
                      <Tag size="small" appearance="brand">
                        {item.complaint}
                      </Tag>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>{item.summary_excerpt}</TableCell>
                  <TableCell>
                    <Button size="small" appearance="subtle">
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "center",
              marginTop: 12,
            }}
          >
            <Button
              size="small"
              disabled={level.offset <= 0 || loading}
              onClick={() =>
                dispatch(setCallsOffset(Math.max(0, level.offset - PAGE_SIZE)))
              }
            >
              Prev
            </Button>
            <Body1>
              Page {page} of {lastPage}
            </Body1>
            <Button
              size="small"
              disabled={level.offset + PAGE_SIZE >= total || loading}
              onClick={() =>
                dispatch(setCallsOffset(level.offset + PAGE_SIZE))
              }
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
};

export default CallList;
