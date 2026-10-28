import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const DEFAULT_API_PROXY_TARGET = "http://localhost:8000";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, "");
  // An empty `API_PROXY_TARGET=` line should still fall back to the default, which `??` would not do.
  const configuredTarget = env.API_PROXY_TARGET ?? "";
  const target = configuredTarget === "" ? DEFAULT_API_PROXY_TARGET : configuredTarget;
  const proxy = { "/api": { target, changeOrigin: true } };

  return {
    plugins: [react()],
    resolve: {
      alias: { "@": `${import.meta.dirname}/src` },
    },
    // Coverage output lands in the watched tree and would otherwise reload the open app.
    // The app is same-origin (dev proxy, production rewrite), so no CORS headers are wanted on /api responses.
    server: { proxy, cors: false, watch: { ignored: ["**/coverage/**"] } },
    preview: { proxy, cors: false },
    build: {
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: "react-vendor",
                test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/,
              },
            ],
          },
        },
      },
    },
  };
});
