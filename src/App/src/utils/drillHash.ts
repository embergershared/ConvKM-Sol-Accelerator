// URL hash encode/decode for drill state — see plans/dashboard-drill-down.md.
// Hash format (Stage B):
//   #/drill/<dimension>=<value>&bucket=<day|week>[&from=<iso>&to=<iso>][&call=<id>]
//
// The encoding intentionally keeps the syntax open enough that Stage C can
// append cross-filter chips (e.g. `&cf=topic:Billing,sentiment:Negative`) and
// extra view state without a breaking change to the parser.

import type {
  DrillBucket,
  DrillDimension,
  DrillLevel,
  DrillSelection,
  DrillTimeRange,
} from "../types/Drill";

const PREFIX = "#/drill/";
const DIMENSIONS: readonly DrillDimension[] = [
  "topic",
  "sentiment",
  "key_phrase",
];

const BUCKETS: readonly DrillBucket[] = ["day", "week"];

export function encodeDrillStack(stack: DrillLevel[]): string {
  if (!stack.length) return "";
  const first = stack[0];
  if (first.kind !== "timeseries") return "";

  const params = new URLSearchParams();
  params.set(first.selection.dimension, first.selection.value);
  params.set("bucket", first.bucket);

  for (const level of stack.slice(1)) {
    if (level.kind === "calls" && level.timeRange) {
      params.set("from", level.timeRange.from);
      params.set("to", level.timeRange.to);
    } else if (level.kind === "transcript") {
      params.set("call", level.conversationId);
    }
  }
  return PREFIX + params.toString();
}

export function decodeDrillStack(hash: string): DrillLevel[] | null {
  if (!hash || !hash.startsWith(PREFIX)) return null;
  const params = new URLSearchParams(hash.slice(PREFIX.length));

  let selection: DrillSelection | null = null;
  for (const dim of DIMENSIONS) {
    const v = params.get(dim);
    if (v) {
      selection = { dimension: dim, value: v };
      break;
    }
  }
  if (!selection) return null;

  const bucketRaw = params.get("bucket") as DrillBucket | null;
  const bucket: DrillBucket =
    bucketRaw && BUCKETS.includes(bucketRaw) ? bucketRaw : "week";

  const stack: DrillLevel[] = [{ kind: "timeseries", selection, bucket }];

  const from = params.get("from");
  const to = params.get("to");
  if (from && to) {
    const timeRange: DrillTimeRange = { from, to };
    stack.push({ kind: "calls", selection, timeRange, offset: 0 });
  }

  const call = params.get("call");
  if (call) {
    if (!from || !to) {
      // A transcript link without a time bucket is still valid; push a calls
      // level with no time_range so the back-arrow lands somewhere sensible.
      stack.push({ kind: "calls", selection, offset: 0 });
    }
    stack.push({ kind: "transcript", conversationId: call });
  }

  return stack;
}
