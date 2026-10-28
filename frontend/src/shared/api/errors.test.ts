import { http, HttpResponse } from "msw";
import createClient from "openapi-fetch";
import { server } from "@/test/msw/server";
import { apiClient } from "./client";
import { ApiError, isGoneError, unwrap } from "./errors";
import type { paths } from "./schema";

const BASE_URL = window.location.origin;
const DATA_URL = `${BASE_URL}/api/v1/widgets/:id/data`;
const WIDGET_ID = "0b1f6a0e-5d3c-4c1e-9d55-2f0a6b7c8d9e";

type Client = ReturnType<typeof createClient<paths>>;

function fetchWidgetData(client: Client) {
  return unwrap(
    client.GET("/api/v1/widgets/{widget_id}/data", { params: { path: { widget_id: WIDGET_ID } } }),
  );
}

describe("unwrap", () => {
  it("returns the data on success", async () => {
    const chart = { categories: ["a"], series: [{ name: "s", values: [1] }] };
    server.use(http.get(DATA_URL, () => HttpResponse.json(chart)));

    await expect(fetchWidgetData(apiClient)).resolves.toEqual(chart);
  });

  it("throws an ApiError with the server's code, message and details", async () => {
    const body = { error: { code: "not_found", message: "Widget not found", details: null } };
    server.use(http.get(DATA_URL, () => HttpResponse.json(body, { status: 404 })));

    const request = fetchWidgetData(apiClient);

    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "not_found",
      message: "Widget not found",
      details: null,
    });
  });

  it("keeps the details the server sends", async () => {
    const details = { fields: [{ message: "Field required" }] };
    const body = { error: { code: "validation_error", message: "Invalid", details } };
    server.use(http.get(DATA_URL, () => HttpResponse.json(body, { status: 422 })));

    await expect(fetchWidgetData(apiClient)).rejects.toMatchObject({ status: 422, details });
  });

  it("falls back to a generic message for non-JSON errors", async () => {
    server.use(
      http.get(DATA_URL, () =>
        HttpResponse.text("<html>Bad gateway</html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    await expect(fetchWidgetData(apiClient)).rejects.toMatchObject({
      status: 502,
      code: "http_502",
      message: "Request failed (502)",
      details: null,
    });
  });

  it("falls back to a generic message when the JSON body has another shape", async () => {
    server.use(http.get(DATA_URL, () => HttpResponse.json({ error: "boom" }, { status: 500 })));

    await expect(fetchWidgetData(apiClient)).rejects.toMatchObject({
      status: 500,
      code: "http_500",
    });
  });

  it("returns undefined for a 204 response", async () => {
    server.use(
      http.delete(`${BASE_URL}/api/v1/widgets/:id`, () => new HttpResponse(null, { status: 204 })),
    );

    const request = unwrap(
      apiClient.DELETE("/api/v1/widgets/{widget_id}", {
        params: { path: { widget_id: WIDGET_ID } },
      }),
    );

    await expect(request).resolves.toBeUndefined();
  });

  it("turns network failures into network_error with status 0 and keeps the cause", async () => {
    server.use(http.get(DATA_URL, () => HttpResponse.error()));

    const request = fetchWidgetData(apiClient);

    await expect(request).rejects.toMatchObject({
      status: 0,
      code: "network_error",
      message: "Network error. Check your connection.",
    });
    await expect(request).rejects.toHaveProperty("cause.name", "TypeError");
  });

  it("rethrows an aborted request as the original error", async () => {
    const abortError = new DOMException("The operation was aborted", "AbortError");
    const failing = createClient<paths>({
      baseUrl: BASE_URL,
      fetch: () => Promise.reject(abortError),
    });

    await expect(fetchWidgetData(failing)).rejects.toBe(abortError);
  });

  it("does not report an unreadable success body as a network error", async () => {
    server.use(
      http.get(DATA_URL, () =>
        HttpResponse.text("<html>proxy page</html>", {
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    const request = fetchWidgetData(apiClient);

    await expect(request).rejects.not.toBeInstanceOf(ApiError);
  });
});

describe("isGoneError", () => {
  it("is true only for 404 ApiErrors", () => {
    const results = [
      isGoneError(new ApiError(404, "not_found", "Gone")),
      isGoneError(new ApiError(500, "boom", "Broken")),
      isGoneError(new Error("404")),
      isGoneError(undefined),
    ];

    expect(results).toEqual([true, false, false, false]);
  });
});
