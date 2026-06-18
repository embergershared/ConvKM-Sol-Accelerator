import React, { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Stack } from "@fluentui/react";
import { DismissRegular } from "@fluentui/react-icons";
import remarkGfm from "remark-gfm";
import { useAppDispatch } from "../../state/hooks";
import { hideCitation } from "../../state/slices/citationSlice";
import { fetchAudioUrl, type AudioAvailability } from "../../api/api";
import "./CitationPanel.css";

/**
 * Extract a conversation ID from a citation title.
 * Citation titles follow the pattern ``{conversationId}_NN`` where NN is a
 * chunk index, or may be the bare conversation ID (a UUID).
 */
function extractConversationId(title?: string): string | null {
  if (!title) return null;
  // Try to find a UUID (8-4-4-4-12 hex) anywhere in the title.
  // Handles formats like:
  //   "2dce8842-a065-44eb-bd8a-2bfa87efd931_01"  (chunk suffix)
  //   "convo_2dce8842-a065-44eb-bd8a-2bfa87efd931_2024-12-04 18_00_00.wav" (WAV filename)
  //   "2dce8842-a065-44eb-bd8a-2bfa87efd931" (bare UUID)
  const match = title.match(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
  );
  return match ? match[0] : null;
}

interface Props {
  activeCitation: any;
}

const CitationPanelComponent: React.FC<Props> = ({ activeCitation }) => {
  const dispatch = useAppDispatch();
  const [audio, setAudio] = useState<AudioAvailability>({ available: false });

  const handleCloseCitation = useCallback(() => {
    dispatch(hideCitation());
  }, [dispatch]);

  const conversationId = extractConversationId(activeCitation?.title);

  useEffect(() => {
    setAudio({ available: false });
    if (!conversationId) return;
    let cancelled = false;
    fetchAudioUrl(conversationId).then((result) => {
      if (!cancelled) setAudio(result);
    });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  return (
    <div className="citationPanel">
      <Stack.Item>
        <Stack
          horizontal
          horizontalAlign="space-between"
          verticalAlign="center"
        >
          <div
            role="heading"
            aria-level={2}
            style={{
              fontWeight: "600",
              fontSize: "16px",
            }}
          >
            Citations
          </div>
          <DismissRegular
            role="button"
            onKeyDown={(event) => {
              if (event.key === " " || event.key === "Enter") {
                event.preventDefault();
                handleCloseCitation();
              }
            }}
            tabIndex={0}
            onClick={handleCloseCitation}
          />
        </Stack>
        <h5>{activeCitation.title}</h5>

        {audio.available && audio.url && (
          <div style={{ marginBottom: 12 }}>
            <audio
              controls
              preload="metadata"
              src={audio.url}
              style={{ width: "100%" }}
            >
              Your browser does not support the audio element.
            </audio>
          </div>
        )}

        <ReactMarkdown
          children={activeCitation?.content}
          remarkPlugins={[remarkGfm]}
        />
      </Stack.Item>
    </div>
  );
};

const CitationPanel = React.memo(CitationPanelComponent);
CitationPanel.displayName = "CitationPanel";

export default CitationPanel;