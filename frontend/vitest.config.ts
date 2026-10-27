import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

const MIN_LINE_COVERAGE = 85;

export default defineConfig((env) =>
  mergeConfig(
    viteConfig(env),
    defineConfig({
      test: {
        globals: true,
        restoreMocks: true,
        environment: "jsdom",
        setupFiles: ["src/test/setup.ts"],
        include: ["src/**/*.test.{ts,tsx}"],
        coverage: {
          provider: "v8",
          include: ["src/**"],
          exclude: [
            "src/shared/api/schema.d.ts",
            "src/main.tsx",
            "src/test/**",
            "**/*.test.*",
            "e2e/**",
          ],
          thresholds: { lines: MIN_LINE_COVERAGE },
        },
      },
    }),
  ),
);
