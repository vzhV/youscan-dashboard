import createClient from "openapi-fetch";
import type { paths } from "./schema";

// An absolute same-origin URL (the Vite proxy in dev, the Vercel rewrite in production) because Node's Request,
// used under test, rejects relative ones. fetch is looked up per call so test interceptors such as MSW, which
// patch the global after this module loads, still see the request.
export const apiClient = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: (request) => globalThis.fetch(request),
});
