import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { importApiPlugin } from "./server/importApiPlugin.ts";
import { assistantApiPlugin } from "./server/assistantApiPlugin.ts";
import { accountApiPlugin } from "./server/accountApiPlugin.ts";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const env = { ...process.env, ...loadEnv(mode, root, "") };
  if (env.ARBOR_AZURE_CLI_DIR?.trim()) {
    process.env.PATH = `${env.ARBOR_AZURE_CLI_DIR}${path.delimiter}${process.env.PATH ?? ""}`;
  }
  // The subprocess pipeline reads server-only settings from process.env.
  for (const [key, value] of Object.entries(env)) {
    if ((key.startsWith("ARBOR3D_") || key === "PYTHON") && value != null) process.env[key] = value;
  }
  return {
    plugins: [
      react(),
      accountApiPlugin(root, env),
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
