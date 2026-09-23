import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { importApiPlugin } from "./server/importApiPlugin.ts";
import { assistantApiPlugin } from "./server/assistantApiPlugin.ts";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const env = { ...process.env, ...loadEnv(mode, root, "") };
  return {
    plugins: [
      react(),
      importApiPlugin(root),
      assistantApiPlugin(env, path.resolve(root, "..", "agents", "knowledge")),
    ],
    server: {
      watch: {
        ignored: [
          "**/inbox/**",
          "**/public/scans/**/_inbox_staged/**",
          "**/*.bag",
          "**/*.ply",
        ],
      },
    },
  };
});
