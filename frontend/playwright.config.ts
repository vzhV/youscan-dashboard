import { defineConfig, devices } from "@playwright/test";

// The webServer entry is added together with the first e2e specs.
export default defineConfig({
  use: { baseURL: "http://localhost:4173" },
  projects: [
    { name: "e2e", testDir: "e2e/specs", use: { ...devices["Desktop Chrome"] } },
    { name: "perf", testDir: "e2e/perf", use: { ...devices["Desktop Chrome"] } },
  ],
});
