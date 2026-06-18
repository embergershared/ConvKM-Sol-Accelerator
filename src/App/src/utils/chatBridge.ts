// Module-level event bus for one-way "Ask AI about this" handoffs.
//
// Why an event bus instead of a Redux thunk?
//   The chat AbortController lives inside the Chat component's useChatApi hook
//   (`hooks/useChatApi.ts:80`), held in a useRef so it is NOT visible to Redux.
//   Refactoring useChatApi to lift the abort handle into Redux would touch a
//   lot of code unrelated to the drill feature. Instead we lean on the
//   *existing* abort path: `useChatApi.ts:82-90` already aborts any in-flight
//   stream when `state.app.selectedConversationId` changes. So the AI handoff
//   in DrillDrawer just needs to:
//     1. caller flips the Chat panel visible if it was hidden
//     2. dispatch(startNewConversation())              // change conversationId -> abort
//     3. dispatchAskAI({ prompt })                     // delivers the prompt
//   and Chat.tsx (subscribed via useEffect) receives the prompt and calls
//   sendMessage(). When the Chat panel was previously hidden, Chat.tsx hasn't
//   mounted at the moment of dispatch — so the bus stores ONE pending request
//   and replays it to the first subscriber that registers within the next
//   PENDING_TTL_MS window. After that window or after delivery the slot is
//   cleared; nothing is persisted across page reloads.

export type AskAIRequest = {
  prompt: string;
  /**
   * Free-form context object the dispatcher may attach (drill stack snapshot,
   * referrer = 'drill' | 'cross_filter' | ...). The subscriber should treat
   * this as advisory; the prompt is the authoritative payload.
   */
  context?: Record<string, unknown>;
};

export type AskAIHandler = (request: AskAIRequest) => void;

/** Pending requests survive at most this long before being silently dropped. */
const PENDING_TTL_MS = 2_000;

const subscribers = new Set<AskAIHandler>();
let pending: { request: AskAIRequest; ts: number } | null = null;

function isPendingFresh(): boolean {
  if (!pending) return false;
  if (Date.now() - pending.ts > PENDING_TTL_MS) {
    pending = null;
    return false;
  }
  return true;
}

/**
 * Register a handler. Returns an unsubscribe function — call it in your
 * useEffect cleanup so React strict-mode double-mount doesn't keep stale
 * subscribers around.
 *
 * If a pending request is queued (e.g. the dispatcher fired before the Chat
 * panel mounted), the new subscriber receives it immediately and the pending
 * slot is cleared.
 */
export function subscribeAskAI(handler: AskAIHandler): () => void {
  subscribers.add(handler);
  if (isPendingFresh() && pending) {
    const { request } = pending;
    pending = null;
    try {
      handler(request);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("[chatBridge] askAI handler threw on replay:", err);
    }
  }
  return () => {
    subscribers.delete(handler);
  };
}

/**
 * Fan-out the request to every registered handler synchronously. If there
 * are no subscribers, the request is held as the pending slot for the next
 * subscriber to consume (within PENDING_TTL_MS). Errors thrown by one
 * handler must not block the others.
 */
export function dispatchAskAI(request: AskAIRequest): void {
  if (subscribers.size === 0) {
    pending = { request, ts: Date.now() };
    return;
  }
  // Snapshot to an array so a handler that unsubscribes mid-iteration doesn't
  // mutate the set we're walking. Also avoids the TS `--downlevelIteration`
  // requirement for `for...of` over Set under the project's es5 target.
  const snapshot: AskAIHandler[] = [];
  subscribers.forEach((h) => snapshot.push(h));
  for (let i = 0; i < snapshot.length; i += 1) {
    try {
      snapshot[i](request);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("[chatBridge] askAI handler threw:", err);
    }
  }
}

/**
 * Test-only — clears all subscribers and any pending request. Production
 * code should not call this.
 */
export function __resetForTests(): void {
  subscribers.clear();
  pending = null;
}

/**
 * Test-only — returns the live subscriber count for assertions.
 */
export function __subscriberCountForTests(): number {
  return subscribers.size;
}

/**
 * Test-only — returns true if a pending request is currently queued.
 */
export function __hasPendingForTests(): boolean {
  return isPendingFresh();
}
