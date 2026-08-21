import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { importApiPlugin } from "./server/importApiPlugin.ts";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), importApiPlugin(root)],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // Allow Cursor / Cloudflare tunnel Host headers
    allowedHosts: true,
    watch: {
      ignored: [
        "**/inbox/**",
        "**/public/scans/**/_inbox_staged/**",
        "**/*.bag",
        "**/*.ply",
      ],
    },
  },
});
