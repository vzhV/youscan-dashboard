const NETWORK_ERROR_STATUS = 0;
const NOT_FOUND_STATUS = 404;

type ApiErrorOptions = {
  readonly details?: Readonly<Record<string, unknown>> | null;
  readonly cause?: unknown;
};

export class ApiError extends Error {
  override readonly name = "ApiError";
  readonly details: Readonly<Record<string, unknown>> | null;

  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    { details = null, cause }: ApiErrorOptions = {},
  ) {
    super(message, { cause });
    this.details = details;
  }
}

type RequestResult<T> = { data?: T; error?: unknown; response: Response };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isErrorBody(
  value: unknown,
): value is Record<string, unknown> & { code: string; message: string } {
  return isRecord(value) && typeof value.code === "string" && typeof value.message === "string";
}

function readDetails(body: Record<string, unknown>): Readonly<Record<string, unknown>> | null {
  return isRecord(body.details) ? body.details : null;
}

export function toApiError(body: unknown, response: Response): ApiError {
  if (isRecord(body) && isErrorBody(body.error)) {
    const { code, message } = body.error;
    return new ApiError(response.status, code, message, { details: readDetails(body.error) });
  }
  return new ApiError(
    response.status,
    `http_${String(response.status)}`,
    `Request failed (${String(response.status)})`,
  );
}

export async function unwrap<T>(request: Promise<RequestResult<T>>): Promise<T> {
  let result: RequestResult<T>;
  try {
    result = await request;
  } catch (error) {
    // fetch rejects with a TypeError when no response arrived; aborts and programming errors must stay visible.
    if (error instanceof TypeError) {
      throw new ApiError(
        NETWORK_ERROR_STATUS,
        "network_error",
        "Network error. Check your connection.",
        { cause: error },
      );
    }
    throw error;
  }
  if (!result.response.ok) {
    throw toApiError(result.error, result.response);
  }
  // Bodiless responses (204, or an empty body) yield undefined data, and T is `undefined` for those endpoints.
  return result.data as T;
}

export function isGoneError(error: unknown): boolean {
  return error instanceof ApiError && error.status === NOT_FOUND_STATUS;
}
