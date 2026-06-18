import {
  __resetForTests,
  __subscriberCountForTests,
  dispatchAskAI,
  subscribeAskAI,
} from "./chatBridge";

describe("chatBridge", () => {
  beforeEach(() => {
    __resetForTests();
  });

  it("delivers a request to every subscriber", () => {
    const a = jest.fn();
    const b = jest.fn();
    subscribeAskAI(a);
    subscribeAskAI(b);

    dispatchAskAI({ prompt: "hello" });

    expect(a).toHaveBeenCalledWith({ prompt: "hello" });
    expect(b).toHaveBeenCalledWith({ prompt: "hello" });
  });

  it("returns an unsubscribe function that removes only that subscriber", () => {
    const a = jest.fn();
    const b = jest.fn();
    const unsubA = subscribeAskAI(a);
    subscribeAskAI(b);
    expect(__subscriberCountForTests()).toBe(2);

    unsubA();
    expect(__subscriberCountForTests()).toBe(1);

    dispatchAskAI({ prompt: "after unsub" });
    expect(a).not.toHaveBeenCalled();
    expect(b).toHaveBeenCalledWith({ prompt: "after unsub" });
  });

  it("isolates handler errors so siblings still receive the request", () => {
    const consoleSpy = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    const throwing = jest.fn(() => {
      throw new Error("boom");
    });
    const sibling = jest.fn();
    subscribeAskAI(throwing);
    subscribeAskAI(sibling);

    dispatchAskAI({ prompt: "test" });

    expect(throwing).toHaveBeenCalled();
    expect(sibling).toHaveBeenCalledWith({ prompt: "test" });
    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("passes the optional context object through unchanged", () => {
    const handler = jest.fn();
    subscribeAskAI(handler);
    const context = { referrer: "drill", level: "transcript", id: "abc-1" };

    dispatchAskAI({ prompt: "summarize", context });

    expect(handler).toHaveBeenCalledWith({ prompt: "summarize", context });
  });

  it("is a no-op when there are no subscribers", () => {
    expect(() => dispatchAskAI({ prompt: "void" })).not.toThrow();
  });

  it("queues a pending request and delivers it to the next subscriber", () => {
    const handler = jest.fn();
    dispatchAskAI({ prompt: "queued" });
    expect(handler).not.toHaveBeenCalled();
    subscribeAskAI(handler);
    expect(handler).toHaveBeenCalledWith({ prompt: "queued" });
  });

  it("delivers the pending request to only ONE subscriber (first wins)", () => {
    const a = jest.fn();
    const b = jest.fn();
    dispatchAskAI({ prompt: "once" });
    subscribeAskAI(a);
    subscribeAskAI(b);
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).not.toHaveBeenCalled();
  });
});
