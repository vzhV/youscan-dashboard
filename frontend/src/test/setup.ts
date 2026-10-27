import "@testing-library/jest-dom/vitest";
import "vitest-canvas-mock";
import { registerConsoleGuard } from "./consoleGuard";
import { installIntersectionObserver, resetIntersectionObserver } from "./intersectionObserver";
import { server } from "./msw/server";

// Ant Design reads matchMedia for responsive breakpoints; jsdom does not provide it.
function stubMatchMedia(): void {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string): MediaQueryList => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      // eslint-disable-next-line @typescript-eslint/no-deprecated -- the MediaQueryList type still requires the legacy members
      addListener: vi.fn(),
      // eslint-disable-next-line @typescript-eslint/no-deprecated -- same reason as addListener
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

// Chart.js observes its canvas container for resizes; jsdom has no layout, so a no-op is enough.
class NoopResizeObserver implements ResizeObserver {
  observe(): void {
    // intentionally empty
  }
  unobserve(): void {
    // intentionally empty
  }
  disconnect(): void {
    // intentionally empty
  }
}

stubMatchMedia();
globalThis.ResizeObserver = NoopResizeObserver;
installIntersectionObserver();
registerConsoleGuard();

beforeAll(() => {
  server.listen({ onUnhandledFrame: "error" });
});
afterEach(() => {
  server.resetHandlers();
  resetIntersectionObserver();
});
afterAll(() => {
  server.close();
});
