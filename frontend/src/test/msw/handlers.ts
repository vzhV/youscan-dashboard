import type { RequestHandler } from "msw";

// Feature tests register their own handlers; the shared list starts empty.
export const handlers: RequestHandler[] = [];
