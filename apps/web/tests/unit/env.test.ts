import { describe, expect, it } from "vitest";

import { parsePublicEnv } from "@/lib/env.schema";

const valid = {
  NEXT_PUBLIC_API_URL: "https://api.example.com/",
  NEXT_PUBLIC_SUPABASE_URL: "https://abc.supabase.co",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon",
};

describe("parsePublicEnv", () => {
  it("accepts valid env and strips the trailing slash from the API URL", () => {
    expect(parsePublicEnv(valid).NEXT_PUBLIC_API_URL).toBe("https://api.example.com");
  });

  it("refuses to start when a required key is missing", () => {
    expect(() => parsePublicEnv({ ...valid, NEXT_PUBLIC_SUPABASE_ANON_KEY: undefined })).toThrow(
      /NEXT_PUBLIC_SUPABASE_ANON_KEY/,
    );
  });

  it("rejects non-URL values", () => {
    expect(() => parsePublicEnv({ ...valid, NEXT_PUBLIC_API_URL: "not a url" })).toThrow(
      /NEXT_PUBLIC_API_URL/,
    );
  });

  it("treats an empty Sentry DSN as unset", () => {
    expect(parsePublicEnv({ ...valid, NEXT_PUBLIC_SENTRY_DSN: "" }).NEXT_PUBLIC_SENTRY_DSN).toBe(
      "",
    );
  });
});
