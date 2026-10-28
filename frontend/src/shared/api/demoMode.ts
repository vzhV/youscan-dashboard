import type { Middleware } from "openapi-fetch";
import { apiClient } from "./client";

export type DemoMode = "slow" | "fail";

export const DEMO_MODES: readonly DemoMode[] = ["slow", "fail"];
export const DEMO_DELAY_MS = 2000;

const DEMO_MODE_VALUES: ReadonlySet<string> = new Set(DEMO_MODES);
const DEMO_QUERY_PARAM = "demo";
const WIDGET_DATA_PATH = /^\/api\/v1\/widgets\/([^/]+)\/data$/;
const SERVICE_UNAVAILABLE_STATUS = 503;

function isDemoMode(value: string): value is DemoMode {
  return DEMO_MODE_VALUES.has(value);
}

export function parseDemoModes(search: string): ReadonlySet<DemoMode> {
  const value = new URLSearchParams(search).get(DEMO_QUERY_PARAM) ?? "";
  return new Set(value.split(",").filter(isDemoMode));
}

// Parsed once at startup: the URL is the only input, so the header tag and the middleware always agree.
export const activeDemoModes: ReadonlySet<DemoMode> = parseDemoModes(window.location.search);

function wait(delayMs: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, delayMs);
  });
}

function createSimulatedFailure(): Response {
  const body = {
    error: {
      code: "demo_failure",
      message: "Simulated failure (demo mode). Press Retry.",
      details: null,
    },
  };
  return new Response(JSON.stringify(body), {
    status: SERVICE_UNAVAILABLE_STATUS,
    headers: { "Content-Type": "application/json" },
  });
}

export function createDemoMiddleware(
  modes: ReadonlySet<DemoMode>,
  delayMs: number = DEMO_DELAY_MS,
): Middleware {
  const failedWidgetIds = new Set<string>();

  return {
    async onRequest({ request }) {
      if (request.method !== "GET") return undefined;
      const widgetId = WIDGET_DATA_PATH.exec(new URL(request.url).pathname)?.[1];
      if (widgetId === undefined) return undefined;

      if (modes.has("slow")) await wait(delayMs);
      // A request abandoned during the delay must not use up the widget's one simulated failure.
      if (request.signal.aborted) return undefined;
      if (modes.has("fail") && !failedWidgetIds.has(widgetId)) {
        failedWidgetIds.add(widgetId);
        return createSimulatedFailure();
      }
      return undefined;
    },
  };
}

export function installDemoMode(modes: ReadonlySet<DemoMode>): Middleware | undefined {
  if (modes.size === 0) return undefined;
  const middleware = createDemoMiddleware(modes);
  apiClient.use(middleware);
  return middleware;
}
