import { env } from "@/lib/env";
import { getAccessToken } from "@/lib/supabase/client";

import { createApiClient } from "./client";

export const api = createApiClient({
  baseUrl: env.NEXT_PUBLIC_API_URL,
  getAccessToken,
});

export { ApiError, isApiError } from "./errors";
export type { ApiClient, ApiMeta, ApiSuccess, RequestOptions } from "./client";
