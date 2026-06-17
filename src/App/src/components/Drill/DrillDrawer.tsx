import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Breadcrumb,
  BreadcrumbButton,
  BreadcrumbDivider,
  BreadcrumbItem,
  Button,
  OverlayDrawer,
  DrawerHeader,
  DrawerHeaderTitle,
  DrawerBody,
  DrawerFooter,
  Tag,
} from "@fluentui/react-components";
import { ArrowLeftRegular, DismissRegular, SparkleRegular } from "@fluentui/react-icons";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import {
  closeDrill,
  popLevel,
  popToDepth,
  resetDrill,
} from "../../state/slices/drillSlice";
import { startNewConversation } from "../../state/slices/appSlice";
import { encodeDrillStack } from "../../utils/drillHash";
import { dispatchAskAI } from "../../utils/chatBridge";
import { buildPromptForStack } from "../../configs/drillPrompts";
import { trackDrillEvent } from "../../utils/drillTelemetry";
import TimeTrendChart from "./TimeTrendChart";
import CallList from "./CallList";
import CallTranscript from "./CallTranscript";
import type { DrillLevel } from "../../types/Drill";
import "./drill.css";

const MIN_WIDTH = 360;
const MAX_WIDTH_VW = 0.95; // 95% of viewport
const DEFAULT_WIDTH = 720;
const STORAGE_KEY = "drill.drawer.width";

function loadStoredWidth(): number {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_WIDTH;
    const n = parseInt(raw, 10);
    if (Number.isFinite(n) && n >= MIN_WIDTH) return n;
  } catch {
    // Ignore — localStorage may be disabled.
  }
  return DEFAULT_WIDTH;
}

function labelForLevel(level: DrillLevel): string {
  switch (level.kind) {
    case "timeseries":
      return `${level.selection.dimension}: ${level.selection.value}`;
    case "calls":
      if (level.timeRange) {
        const from = new Date(level.timeRange.from).toLocaleDateString();
        return `From ${from}`;
      }
      return "Calls";
    case "transcript":
      return `Call ${level.conversationId.slice(0, 8)}…`;
  }
}

const DrillDrawer: React.FC<{ onRequestShowChat?: () => void }> = ({
  onRequestShowChat,
}) => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((s) => s.drill.isOpen);
  const stack = useAppSelector((s) => s.drill.stack);
  const call = useAppSelector((s) => s.drill.call);

  const top = stack[stack.length - 1];
  // At L3, the "Ask AI" button shouldn't dispatch until the transcript has
  // loaded — otherwise the prompt falls back to a generic per-topic version
  // and the user loses the per-call specificity they asked for.
  const askAIDisabled =
    stack.length === 0 ||
    (top?.kind === "transcript" && (!call || !call.transcript_raw));

  const handleAskAI = useCallback(() => {
    if (!stack.length) return;
    if (top?.kind === "transcript" && (!call || !call.transcript_raw)) {
      return;
    }
    const prompt = buildPromptForStack(stack, call ?? undefined);
    if (!prompt) return;
    const level = top?.kind ?? "timeseries";
    const selectionLevel = [...stack]
      .reverse()
      .find((l) => l.kind !== "transcript") as
      | (DrillLevel & { kind: "timeseries" | "calls" })
      | undefined;
    trackDrillEvent("AIHandoffClicked", {
      level,
      dimension: selectionLevel?.selection.dimension,
      value: selectionLevel?.selection.value,
      conversationId:
        top?.kind === "transcript" ? top.conversationId : undefined,
    });
    onRequestShowChat?.();
    // Close the drill drawer — it overlays the right side of the layout where
    // the Chat panel lives, so leaving it open hides the streamed reply.
    // closeDrill preserves the drill stack (vs resetDrill); user can re-open
    // from the URL hash or by clicking the chart mark again.
    dispatch(closeDrill());
    // Change conversation id BEFORE dispatching the prompt so useChatApi's
    // existing abort-on-conversation-change effect tears down any in-flight
    // stream. The chatBridge holds the request as "pending" if Chat hasn't
    // mounted yet (panel was hidden); the first subscriber consumes it.
    dispatch(startNewConversation());
    dispatchAskAI({
      prompt,
      context: {
        referrer: "drill",
        level,
        dimension: selectionLevel?.selection.dimension,
      },
    });
  }, [call, dispatch, onRequestShowChat, stack, top]);

  // Resizable width — drag the handle on the left edge. Persisted to
  // localStorage so the user's preference survives sessions.
  const [width, setWidth] = useState<number>(() => loadStoredWidth());
  const dragStateRef = useRef<{ startX: number; startWidth: number } | null>(
    null
  );

  const onDragMove = useCallback((e: MouseEvent) => {
    const drag = dragStateRef.current;
    if (!drag) return;
    const delta = drag.startX - e.clientX; // dragging left increases width
    const maxWidth = Math.floor(window.innerWidth * MAX_WIDTH_VW);
    const next = Math.min(
      maxWidth,
      Math.max(MIN_WIDTH, drag.startWidth + delta)
    );
    setWidth(next);
  }, []);

  const onDragEnd = useCallback(() => {
    if (!dragStateRef.current) return;
    dragStateRef.current = null;
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
    window.removeEventListener("mousemove", onDragMove);
    window.removeEventListener("mouseup", onDragEnd);
    try {
      window.localStorage.setItem(STORAGE_KEY, String(width));
    } catch {
      // Ignore.
    }
  }, [onDragMove, width]);

  const onDragStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragStateRef.current = { startX: e.clientX, startWidth: width };
      document.body.style.userSelect = "none";
      document.body.style.cursor = "ew-resize";
      window.addEventListener("mousemove", onDragMove);
      window.addEventListener("mouseup", onDragEnd);
    },
    [onDragEnd, onDragMove, width]
  );

  // Clamp width if the viewport shrinks below the stored preference.
  useEffect(() => {
    const onResize = () => {
      const maxWidth = Math.floor(window.innerWidth * MAX_WIDTH_VW);
      setWidth((w) => (w > maxWidth ? maxWidth : w));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        e.preventDefault();
        dispatch(popLevel());
      }
    },
    [dispatch, isOpen]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Sync stack -> window.location.hash (Stage B).
  useEffect(() => {
    if (!isOpen) {
      if (window.location.hash.startsWith("#/drill/")) {
        window.history.replaceState(
          null,
          "",
          window.location.pathname + window.location.search
        );
      }
      return;
    }
    const encoded = encodeDrillStack(stack);
    if (encoded && encoded !== window.location.hash) {
      window.history.replaceState(null, "", encoded);
    }
  }, [isOpen, stack]);

  const renderLevel = useMemo(() => {
    if (!top) return null;
    if (top.kind === "timeseries") return <TimeTrendChart />;
    if (top.kind === "calls") return <CallList />;
    if (top.kind === "transcript") return <CallTranscript />;
    return null;
  }, [top]);

  return (
    <OverlayDrawer
      open={isOpen}
      onOpenChange={(_, data) => {
        if (!data.open) dispatch(resetDrill());
      }}
      position="end"
      size="medium"
      style={{ width: `${width}px`, maxWidth: "95vw" }}
    >
      <div
        className="drill-resize-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize drill drawer"
        title="Drag to resize"
        onMouseDown={onDragStart}
      />
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <div style={{ display: "flex", gap: 4 }}>
              <Button
                appearance="primary"
                size="small"
                icon={<SparkleRegular />}
                title={
                  askAIDisabled && top?.kind === "transcript"
                    ? "Waiting for transcript to load…"
                    : "Seed the chat with a prompt about this drill view"
                }
                disabled={askAIDisabled}
                onClick={handleAskAI}
              >
                Ask AI about this
              </Button>
              <Button
                appearance="subtle"
                icon={<ArrowLeftRegular />}
                aria-label="Back"
                disabled={stack.length <= 1}
                onClick={() => dispatch(popLevel())}
              />
              <Button
                appearance="subtle"
                icon={<DismissRegular />}
                aria-label="Close drill"
                onClick={() => dispatch(closeDrill())}
              />
            </div>
          }
        >
          <Breadcrumb size="small">
            <BreadcrumbItem>
              <BreadcrumbButton onClick={() => dispatch(popToDepth(1))}>
                All
              </BreadcrumbButton>
            </BreadcrumbItem>
            {stack.map((level, idx) => (
              <React.Fragment key={idx}>
                <BreadcrumbDivider />
                <BreadcrumbItem>
                  <BreadcrumbButton
                    current={idx === stack.length - 1}
                    onClick={() => dispatch(popToDepth(idx + 1))}
                  >
                    {labelForLevel(level)}
                  </BreadcrumbButton>
                </BreadcrumbItem>
              </React.Fragment>
            ))}
          </Breadcrumb>
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <div className="drill-drawer-body">{renderLevel}</div>
      </DrawerBody>
      <DrawerFooter>
        <div className="drill-footer" style={{ width: "100%" }}>
          <Tag size="extra-small" shape="circular">
            AI-generated content may be incorrect
          </Tag>
          <Button
            size="small"
            appearance="subtle"
            onClick={() => dispatch(resetDrill())}
          >
            Reset drill
          </Button>
        </div>
      </DrawerFooter>
    </OverlayDrawer>
  );
};

export default DrillDrawer;
