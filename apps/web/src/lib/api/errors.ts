export type ApiErrorCode =
  | "validation_error"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "unprocessable"
  | "rate_limited"
  | "budget_exceeded"
  | "upstream_error"
  | "llm_unavailable"
  | "network_error"
  | "timeout"
  | "unknown_error"
  | (string & {});

export interface ApiErrorInit {
  status: number;
  code: ApiErrorCode;
  message: string;
  requestId?: string;
  details?: Record<string, unknown>;
  retryAfterSeconds?: number;
}

/** Normalised form of the API error envelope {error:{code,message,requestId,details}}. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly requestId?: string;
  readonly details?: Record<string, unknown>;
  readonly retryAfterSeconds?: number;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.requestId = init.requestId;
    this.details = init.details;
    this.retryAfterSeconds = init.retryAfterSeconds;
  }

  /** 5xx, network failures and rate limits are worth retrying; other 4xx are not. */
  get isRetryable(): boolean {
    return this.status === 0 || this.status >= 500 || this.code === "rate_limited";
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

const STATUS_FALLBACK_CODE: Record<number, ApiErrorCode> = {
  400: "validation_error",
  401: "unauthorized",
  403: "forbidden",
  404: "not_found",
  409: "conflict",
  422: "unprocessable",
  429: "rate_limited",
  502: "upstream_error",
  503: "llm_unavailable",
};

export function parseRetryAfter(value: string | null): number | undefined {
  if (!value) return undefined;
  const seconds = Number(value);
  if (Number.isFinite(seconds)) return Math.max(0, seconds);
  const date = Date.parse(value);
  if (Number.isNaN(date)) return undefined;
  return Math.max(0, Math.round((date - Date.now()) / 1000));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Build an ApiError from a non-2xx Response, tolerating non-JSON bodies. */
export async function apiErrorFromResponse(
  response: Response,
  fallbackRequestId?: string,
): Promise<ApiError> {
  const headerRequestId = response.headers.get("x-request-id") ?? fallbackRequestId;
  const retryAfterSeconds = parseRetryAfter(response.headers.get("retry-after"));
  let body: unknown = undefined;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }
  const envelope = isRecord(body) && isRecord(body.error) ? body.error : undefined;
  return new ApiError({
    status: response.status,
    code:
      typeof envelope?.code === "string"
        ? envelope.code
        : (STATUS_FALLBACK_CODE[response.status] ?? "unknown_error"),
    message:
      typeof envelope?.message === "string"
        ? envelope.message
        : response.statusText || `Request failed with status ${response.status}`,
    requestId: typeof envelope?.requestId === "string" ? envelope.requestId : headerRequestId,
    details: isRecord(envelope?.details) ? envelope.details : undefined,
    retryAfterSeconds,
  });
}
