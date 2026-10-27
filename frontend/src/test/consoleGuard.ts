import { afterEach, beforeEach, expect, vi, type MockInstance } from "vitest";

let errorSpy: MockInstance<typeof console.error>;
let warnSpy: MockInstance<typeof console.warn>;

/** Tests that expect React or a library to log an error call this to claim (and clear) those calls. */
export function consumeConsoleErrors(): unknown[][] {
  const calls = [...errorSpy.mock.calls];
  errorSpy.mockClear();
  return calls;
}

export function registerConsoleGuard(): void {
  beforeEach(() => {
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
  });

  afterEach(() => {
    expect(errorSpy.mock.calls, "unexpected console.error").toEqual([]);
    expect(warnSpy.mock.calls, "unexpected console.warn").toEqual([]);
  });
}
