// Drill-down telemetry helper. We avoid adding a new App Insights JS dependency
// in Stage B — the backend already wires Application Insights via OpenTelemetry,
// and the frontend has no @microsoft/applicationinsights-web package today.
//
// This shim logs structured events to the browser console so the names appear
// in any "DevTools → Console" capture and in Application Insights browser
// telemetry when it is added in a follow-up. The exported function signature
// matches `appInsights.trackEvent({ name, properties })` so swapping to the
// real SDK later is a one-line change.

export type DrillEventName =
  | "DrillOpened"
  | "DrillLevelChanged"
  | "DrillCallViewed"
  | "DrillResetClicked"
  | "DrillBackPressed"
  | "CrossFilterApplied"
  | "CrossFilterRemoved"
  | "InvestigateClicked"
  | "AIHandoffClicked";

type DrillEventProperties = {
  dimension?: string;
  value?: string;
  level?: string;
  bucket?: string;
  conversationId?: string;
  source?: "chart" | "manual" | "hash";
  chart?: string;
};

export function trackDrillEvent(
  name: DrillEventName,
  properties: DrillEventProperties = {}
): void {
  try {
    const w = window as unknown as {
      appInsights?: { trackEvent: (e: { name: string; properties?: object }) => void };
    };
    if (w.appInsights && typeof w.appInsights.trackEvent === "function") {
      w.appInsights.trackEvent({ name, properties });
      return;
    }
  } catch {
    // Ignore — fall through to console logging below.
  }
  // eslint-disable-next-line no-console
  console.info(`[telemetry] ${name}`, properties);
}
