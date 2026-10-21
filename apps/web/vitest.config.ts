import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    env: {
      NEXT_PUBLIC_API_URL: "http://api.test",
      NEXT_PUBLIC_SUPABASE_URL: "http://supabase.test",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key",
    },
    coverage: { provider: "v8", include: ["src/**/*.{ts,tsx}"] },
  },
});
