import { http, HttpResponse } from "msw";
import createClient from "openapi-fetch";
import { server } from "@/test/msw/server";
import { apiClient } from "./client";
import {
  createDemoMiddleware,
  DEMO_DELAY_MS,
  installDemoMode,
  parseDemoModes,
  type DemoMode,
} from "./demoMode";
import type { paths } from "./schema";

const BASE_URL = window.location.origin;
const FIRST_ID = "0b1f6a0e-5d3c-4c1e-9d55-2f0a6b7c8d9e";
const SECOND_ID = "9c2d7e1f-3a4b-4c5d-8e6f-7a8b9c0d1e2f";

function createDemoClient(modes: DemoMode[], delayMs?: number) {
  const client = createClient<paths>({ baseUrl: BASE_URL });
  client.use(createDemoMiddleware(new Set(modes), delayMs));
  return client;
}

function fetchData(client: ReturnType<typeof createDemoClient>, widgetId: string) {
  return client.GET("/api/v1/widgets/{widget_id}/data", {
    params: { path: { widget_id: widgetId } },
  });
}

beforeEach(() => {
  server.use(
    http.get(`${BASE_URL}/api/v1/widgets/:id/data`, () =>
      HttpResponse.json({ categories: [], series: [] }),
    ),
    http.get(`${BASE_URL}/api/v1/widgets`, () => HttpResponse.json([])),
  );
});

describe("parseDemoModes", () => {
  it("reads comma separated modes and ignores unknown ones", () => {
    expect(parseDemoModes("?demo=slow,fail,x")).toEqual(new Set(["slow", "fail"]));
  });

  it("returns no modes when the demo parameter is absent", () => {
    expect(parseDemoModes("?other=1").size).toBe(0);
  });
});

describe("demo middleware", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("slow mode delays widget data requests by 2000 ms", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    let isSettled = false;

    const request = fetchData(createDemoClient(["slow"]), FIRST_ID).then((result) => {
      isSettled = true;
      return result;
    });
    await vi.advanceTimersByTimeAsync(DEMO_DELAY_MS - 1);
    expect(isSettled).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    const { response } = await request;

    expect(response.status).toBe(200);
  });

  it("fail mode fails the first data request per widget then lets it through", async () => {
    const client = createDemoClient(["fail"]);

    const first = await fetchData(client, FIRST_ID);
    const retry = await fetchData(client, FIRST_ID);
    const other = await fetchData(client, SECOND_ID);

    expect(first.response.status).toBe(503);
    expect(first.error).toEqual({
      error: {
        code: "demo_failure",
        message: "Simulated failure (demo mode). Press Retry.",
        details: null,
      },
    });
    expect(retry.response.status).toBe(200);
    expect(other.response.status).toBe(503);
  });

  it("ignores other requests", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const client = createDemoClient(["slow", "fail"]);

    const { response } = await client.GET("/api/v1/widgets");

    expect(response.status).toBe(200);
  });

  it("does not spend the simulated failure on a request aborted during the delay", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const client = createDemoClient(["slow", "fail"]);
    const controller = new AbortController();

    const abandoned = client
      .GET("/api/v1/widgets/{widget_id}/data", {
        params: { path: { widget_id: FIRST_ID } },
        signal: controller.signal,
      })
      .catch((error: unknown) => error);
    controller.abort();
    await vi.advanceTimersByTimeAsync(DEMO_DELAY_MS);
    await abandoned;
    const retry = fetchData(client, FIRST_ID);
    await vi.advanceTimersByTimeAsync(DEMO_DELAY_MS);

    expect((await retry).response.status).toBe(503);
  });

  it("ignores non-GET requests to the data path", async () => {
    const middleware = createDemoMiddleware(new Set<DemoMode>(["fail"]));
    const request = new Request(`${BASE_URL}/api/v1/widgets/${FIRST_ID}/data`, { method: "PATCH" });

    const result = await middleware.onRequest?.({
      request,
      schemaPath: "",
      params: {},
      id: "",
      // The middleware ignores the options; the cast spares building a full client options object.
      options: {} as never,
    });

    expect(result).toBeUndefined();
  });
});

describe("installDemoMode", () => {
  let installed: ReturnType<typeof installDemoMode>;

  afterEach(() => {
    if (installed) apiClient.eject(installed);
    installed = undefined;
  });

  it("installs nothing when no modes are active", () => {
    installed = installDemoMode(new Set());

    expect(installed).toBeUndefined();
  });

  it("installs the middleware on the shared client when modes are active", async () => {
    installed = installDemoMode(new Set<DemoMode>(["fail"]));

    const { response } = await apiClient.GET("/api/v1/widgets/{widget_id}/data", {
      params: { path: { widget_id: FIRST_ID } },
    });

    expect(response.status).toBe(503);
  });
});
