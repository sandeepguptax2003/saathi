import { z } from "zod";

/** Browser-safe env only. Anything secret must never be NEXT_PUBLIC_. */
export const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.url({ protocol: /^https?$/ }),
  NEXT_PUBLIC_SUPABASE_URL: z.url({ protocol: /^https?$/ }),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_SENTRY_DSN: z.union([z.url(), z.literal("")]).optional(),
});

export type PublicEnv = z.infer<typeof publicEnvSchema>;

export function parsePublicEnv(raw: Record<string, string | undefined>): PublicEnv {
  const result = publicEnvSchema.safeParse(raw);
  if (!result.success) {
    const issues = result.error.issues
      .map((issue) => `${issue.path.join(".") || "(root)"}: ${issue.message}`)
      .join("; ");
    throw new Error(`Invalid public environment. ${issues}. See apps/web/.env.example.`);
  }
  return {
    ...result.data,
    NEXT_PUBLIC_API_URL: result.data.NEXT_PUBLIC_API_URL.replace(/\/+$/, ""),
  };
}
