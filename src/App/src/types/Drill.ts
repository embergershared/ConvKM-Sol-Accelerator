// Drill-down types — see plans/dashboard-drill-down.md (Stage B).
// Backend response shapes are mirrored from src/api/api/models/input_models.py
// and the new fetch fns in src/api/common/database/sqldb_service.py.

export type DrillDimension = "topic" | "sentiment" | "key_phrase";
export type DrillBucket = "day" | "week";

export type DrillSelection = {
  dimension: DrillDimension;
  value: string;
};

export type DrillTimeRange = {
  from: string; // ISO datetime, inclusive
  to: string;   // ISO datetime, exclusive
};

// Discriminated union — one variant per drill level.
export type DrillLevel =
  | {
      kind: "timeseries";
      selection: DrillSelection;
      bucket: DrillBucket;
    }
  | {
      kind: "calls";
      selection: DrillSelection;
      timeRange?: DrillTimeRange;
      offset: number;
    }
  | {
      kind: "transcript";
      conversationId: string;
    };

export type TimeseriesPoint = {
  bucket_start: string;        // ISO datetime
  calls: number;
  avg_sentiment_score: number; // [-1, 1]
  satisfied_pct: number;       // [0, 100]
  avg_handle_time_min: number;
};

export type CallListItem = {
  conversation_id: string;
  start_time: string;          // ISO datetime
  duration_min: number;
  sentiment: string;           // "Positive" | "Neutral" | "Negative"
  satisfied: string;           // "Yes" | "No"
  topic: string;
  complaint: string | null;
  summary_excerpt: string;     // first 80 chars of summary
};

export type CallDetail = {
  conversation_id: string;
  start_time: string;
  end_time: string;
  duration_min: number;
  sentiment: string;
  satisfied: string;
  topic: string;
  complaint: string | null;
  key_phrases: string[];
  summary: string;
  transcript_raw: string;      // raw processed_data.Content blob
  audio_url?: string;          // SAS URL for call recording playback (if available)
};
