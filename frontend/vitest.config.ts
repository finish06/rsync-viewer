import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    // A real origin so localStorage/cookies exist (about:blank has none)
    environmentOptions: { jsdom: { url: "http://localhost/app" } },
    globals: false,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/test/**", "src/**/*.test.{ts,tsx}", "src/api/types.ts"],
      thresholds: { lines: 80, functions: 80, branches: 70, statements: 80 },
      reporter: ["text", "html"],
    },
  },
});
