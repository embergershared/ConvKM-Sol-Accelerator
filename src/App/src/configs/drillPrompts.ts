// Drill-down "Ask AI about this" prompt templates (Stage C).
//
// Keyed by { level, dimension } -> a template string with named {placeholders}.
// All formatting happens client-side via format() below. The registry is a
// plain TS object so a follow-up iteration can lift it into an Admin UI
// without backend churn (see Resolved decisions §2).
//
// Template style: deliberately matches the natural-language demo prompts in
// Emm-Demo-prompts.md that we know the existing KM-ConversationAgent handles
// well. Avoid:
//   - ISO-millisecond timestamps (agent's date-range tools want short dates)
//   - Bare conversation-id references like "Conversation <uuid>" (agent has
//     no direct id lookup; we inline the transcript text instead at L3).

import type {
  CallDetail,
  DrillBucket,
  DrillDimension,
  DrillLevel,
  DrillSelection,
} from "../types/Drill";

export type PromptPlaceholders = {
  value?: string;
  dimension?: string;
  bucket?: DrillBucket;
  from?: string;     // ISO datetime — formatted to YYYY-MM-DD before substitution
  to?: string;       // ISO datetime — formatted to YYYY-MM-DD before substitution
  conversationId?: string;
};

const DEFAULT_TIMESERIES: Record<DrillDimension, string> = {
  topic:
    "Give me a summary of the recent customer calls about {value}. " +
    "What are the top 3 themes and the most common customer complaints?",
  sentiment:
    "What are the main drivers of {value} customer sentiment in recent calls? " +
    "Identify the top 3 topics driving this sentiment and give one coaching recommendation per topic.",
  key_phrase:
    "What's the underlying customer issue when calls mention '{value}'? " +
    "Summarize the top 3 themes and recommend one product or process improvement.",
};

const DEFAULT_CALLS: Record<DrillDimension, string> = {
  topic:
    "Summarize the recent customer calls about {value} during the week of {from}. " +
    "What are the most common reasons for dissatisfaction and what would you recommend?",
  sentiment:
    "Identify the main drivers of {value} customer sentiment during the week of {from}. " +
    "List the top 3 root causes and one process recommendation for each.",
  key_phrase:
    "Summarize the recent customer concerns where calls mention '{value}' during the week of {from}. " +
    "Suggest two next-best actions for the agents.",
};

/**
 * Transcript-level template. We inline the full transcript text directly in
 * the prompt rather than referencing the conversation id — the agent has no
 * direct id-lookup tool, but it can absolutely reason about a transcript that
 * is part of the prompt itself.
 */
const TRANSCRIPT_TEMPLATE =
  "Here is the transcript of a customer call (Conversation {conversationId}):\n\n" +
  "---\n" +
  "{transcript}\n" +
  "---\n\n" +
  "Summarize the customer's complaint, the agent's resolution, and rate the agent's " +
  "empathy on a scale of 1-5 with one-line reasoning. End with one concrete coaching " +
  "suggestion for the agent.";

/**
 * The full template registry. Public so tests can assert coverage of every
 * { level, dimension } combination.
 */
export const DRILL_PROMPT_TEMPLATES: {
  timeseries: Record<DrillDimension, string>;
  calls: Record<DrillDimension, string>;
  transcript: string;
} = {
  timeseries: DEFAULT_TIMESERIES,
  calls: DEFAULT_CALLS,
  transcript: TRANSCRIPT_TEMPLATE,
};

/** Truncate an ISO timestamp to the YYYY-MM-DD slice. Empty strings pass through. */
function shortDate(iso?: string): string | undefined {
  if (!iso) return iso;
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
  const match = iso.match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : iso;
}

/**
 * Substitute `{name}` placeholders with values from `vars`. Missing or
 * empty values are replaced with "unspecified" so the prompt is always
 * grammatical (rather than leaking a `{from}` literal into the chat).
 *
 * Date fields (`from`, `to`) are short-formatted to YYYY-MM-DD before
 * substitution so the chat agent sees a clean date the RAG date-range tools
 * already understand.
 *
 * The `transcript` placeholder (used only by the L3 template) is also
 * supported here so unit tests can exercise it without going through
 * buildPromptForStack.
 */
export function format(
  template: string,
  vars: PromptPlaceholders & { transcript?: string }
): string {
  const normalized = {
    ...vars,
    from: shortDate(vars.from),
    to: shortDate(vars.to),
  };
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    const v = (normalized as Record<string, unknown>)[key];
    if (v === undefined || v === null || v === "") return "unspecified";
    return String(v);
  });
}

/**
 * Build the AI prompt for the *current* drill stack. The top of the stack
 * decides the level (timeseries / calls / transcript); the selection used
 * is the deepest non-transcript selection in the stack.
 *
 * For the transcript level, pass the loaded CallDetail (from
 * `state.drill.call`) as the second argument so the full transcript text is
 * inlined into the prompt. If `callDetail` is undefined (transcript hasn't
 * finished loading yet) the prompt falls back to a generic per-dimension
 * version that the caller may decide to suppress.
 */
export function buildPromptForStack(
  stack: DrillLevel[],
  callDetail?: CallDetail | null
): string {
  if (!stack.length) return "";
  const top = stack[stack.length - 1];
  const selectionLevel = [...stack]
    .reverse()
    .find(
      (l): l is Extract<DrillLevel, { selection: DrillSelection }> =>
        l.kind !== "transcript"
    );
  const selection = selectionLevel?.selection;
  const dim = (selection?.dimension ?? "topic") as DrillDimension;

  if (top.kind === "transcript") {
    if (callDetail && callDetail.transcript_raw) {
      return format(TRANSCRIPT_TEMPLATE, {
        value: selection?.value,
        dimension: selection?.dimension,
        conversationId: top.conversationId,
        transcript: callDetail.transcript_raw,
      });
    }
    // Fallback when the transcript hasn't loaded yet — steer the agent via
    // the topic context rather than asking it to look up the id.
    return format(DEFAULT_TIMESERIES[dim], {
      value: selection?.value,
      dimension: selection?.dimension,
    });
  }

  if (top.kind === "calls") {
    return format(DEFAULT_CALLS[dim], {
      value: selection?.value,
      dimension: selection?.dimension,
      from: top.timeRange?.from,
      to: top.timeRange?.to,
    });
  }

  // timeseries
  return format(DEFAULT_TIMESERIES[dim], {
    value: selection?.value,
    dimension: selection?.dimension,
    bucket: top.bucket,
  });
}
