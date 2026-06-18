import React, { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../state/hooks";
import { fetchCallDetail, fetchAudioUrl, type AudioAvailability } from "../../api/api";
import {
  setCall,
  setError,
  setLoading,
} from "../../state/slices/drillSlice";
import {
  Body1,
  Button,
  Spinner,
  Subtitle2,
  Tag,
} from "@fluentui/react-components";
import type { DrillLevel } from "../../types/Drill";
import "./drill.css";

const CallTranscript: React.FC = () => {
  const dispatch = useAppDispatch();
  const stack = useAppSelector((s) => s.drill.stack);
  const call = useAppSelector((s) => s.drill.call);
  const loading = useAppSelector((s) => s.drill.loading);
  const error = useAppSelector((s) => s.drill.error);
  const [audio, setAudio] = useState<AudioAvailability>({ available: false });

  const level = stack.find((l) => l.kind === "transcript") as
    | (DrillLevel & { kind: "transcript" })
    | undefined;

  useEffect(() => {
    if (!level) return;
    let cancelled = false;
    (async () => {
      dispatch(setLoading(true));
      try {
        const [data, audioResult] = await Promise.all([
          fetchCallDetail(level.conversationId),
          fetchAudioUrl(level.conversationId),
        ]);
        if (!cancelled) {
          dispatch(setCall(data));
          setAudio(audioResult);
        }
      } catch (e: any) {
        if (!cancelled)
          dispatch(setError(e?.message ?? "Failed to load transcript"));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, level?.conversationId]);

  if (!level) return null;

  if (loading) {
    return (
      <div className="drill-loading">
        <Spinner size="tiny" />
        <Body1>Loading transcript…</Body1>
      </div>
    );
  }
  if (error) return <div className="drill-error">{error}</div>;
  if (!call) return <div className="drill-empty">No transcript loaded.</div>;

  return (
    <div>
      <div className="drill-header-chips">
        <Subtitle2 title={call.conversation_id}>
          Call {call.conversation_id.slice(0, 8)}…
        </Subtitle2>
        <Tag size="small" appearance="outline">
          {new Date(call.start_time).toLocaleString()}
        </Tag>
        <Tag size="small" appearance="outline">
          {call.duration_min} min
        </Tag>
        <Tag size="small" appearance="outline">
          Sentiment: {call.sentiment}
        </Tag>
        <Tag size="small" appearance="outline">
          Satisfied: {call.satisfied}
        </Tag>
        {call.topic && (
          <Tag size="small" appearance="brand">
            {call.topic}
          </Tag>
        )}
        {call.complaint && (
          <Tag size="small" appearance="brand">
            Complaint: {call.complaint}
          </Tag>
        )}
      </div>

      {call.key_phrases.length > 0 && (
        <div className="drill-header-chips" style={{ marginTop: 8 }}>
          {call.key_phrases.map((p) => (
            <Tag key={p} size="extra-small" appearance="outline">
              {p}
            </Tag>
          ))}
        </div>
      )}

      {audio.available && audio.url && (
        <div style={{ marginTop: 12 }}>
          <Subtitle2 as="h3" block>
            Recording
          </Subtitle2>
          <audio
            controls
            preload="metadata"
            src={audio.url}
            style={{ width: "100%", marginTop: 4 }}
          >
            Your browser does not support the audio element.
          </audio>
        </div>
      )}

      {call.summary && (
        <div style={{ marginTop: 12 }}>
          <Subtitle2 as="h3" block>
            Summary
          </Subtitle2>
          <Body1 as="p" block style={{ marginTop: 4 }}>
            {call.summary}
          </Body1>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <Subtitle2 as="h3" block>
          Transcript
        </Subtitle2>
        <pre className="drill-transcript-pre">{call.transcript_raw}</pre>
      </div>

      {/* Stage C will wire this button to seed the Chat agent with drill context. */}
      <div style={{ marginTop: 12 }}>
        <Button size="small" disabled title="Available in Stage C">
          Open in Chat as context
        </Button>
      </div>
    </div>
  );
};

export default CallTranscript;
