import { createReadStream, promises as fs } from "node:fs";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { accountApiPlugin } from "./accountApiPlugin.js";
import { assistantApiPlugin } from "./assistantApiPlugin.js";
import { importApiPlugin } from "./importApiPlugin.js";

type Next = (error?: unknown) => void;
type Middleware = (
  req: IncomingMessage,
  res: ServerResponse,
  next: Next,
) => void | Promise<void>;

const serverFolder = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(serverFolder, "..");
const staticRoot = path.join(appRoot, "dist");
const knowledgeFolder = process.env.ARBOR_RAG_KNOWLEDGE?.trim()
  || path.join(appRoot, "knowledge");
const middleware: Middleware[] = [];
const middlewareHost = {
  middlewares: {
    use(handler: Middleware) {
      middleware.push(handler);
    },
  },
};

for (const plugin of [
  accountApiPlugin(appRoot, process.env),
  importApiPlugin(appRoot),
  assistantApiPlugin(process.env, knowledgeFolder),
]) {
  const configure = plugin.configureServer as
    | ((server: typeof middlewareHost) => void)
    | undefined;
  configure?.(middlewareHost);
}

const mimeTypes: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml; charset=utf-8",
  ".webp": "image/webp",
};

function fail(res: ServerResponse, error: unknown) {
  if (res.writableEnded) return;
  console.error(error);
  res.statusCode = 500;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify({ error: "伺服器暫時無法處理請求" }));
}

async function serveStatic(req: IncomingMessage, res: ServerResponse) {
  const requestUrl = new URL(req.url ?? "/", "http://localhost");
  if (requestUrl.pathname.startsWith("/api/")) {
    res.statusCode = 404;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ error: "找不到 API" }));
    return;
  }

  let pathname: string;
  try {
    pathname = decodeURIComponent(requestUrl.pathname);
  } catch {
    res.statusCode = 400;
    res.end("Bad request");
    return;
  }
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  let filename = path.resolve(staticRoot, relative);
  if (filename !== staticRoot && !filename.startsWith(`${staticRoot}${path.sep}`)) {
    res.statusCode = 403;
    res.end("Forbidden");
    return;
  }

  let stat = await fs.stat(filename).catch(() => null);
  if (!stat?.isFile() && !path.extname(relative)) {
    filename = path.join(staticRoot, "index.html");
    stat = await fs.stat(filename).catch(() => null);
  }
  if (!stat?.isFile()) {
    res.statusCode = 404;
    res.end("Not found");
    return;
  }

  const extension = path.extname(filename).toLowerCase();
  res.statusCode = 200;
  res.setHeader("Content-Type", mimeTypes[extension] || "application/octet-stream");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "same-origin");
  res.setHeader(
    "Cache-Control",
    path.basename(filename) === "index.html"
      ? "no-cache"
      : filename.includes(`${path.sep}assets${path.sep}`)
        ? "public, max-age=31536000, immutable"
        : "public, max-age=300",
  );
  res.setHeader("Content-Length", stat.size);
  if (req.method === "HEAD") {
    res.end();
    return;
  }
  createReadStream(filename).on("error", (error) => fail(res, error)).pipe(res);
}

function dispatch(req: IncomingMessage, res: ServerResponse, index = 0) {
  if (res.writableEnded) return;
  const handler = middleware[index];
  if (!handler) {
    void serveStatic(req, res).catch((error) => fail(res, error));
    return;
  }
  let continued = false;
  const next: Next = (error) => {
    if (continued || res.writableEnded) return;
    continued = true;
    if (error) fail(res, error);
    else dispatch(req, res, index + 1);
  };
  try {
    Promise.resolve(handler(req, res, next)).catch((error) => fail(res, error));
  } catch (error) {
    fail(res, error);
  }
}

const port = Number.parseInt(process.env.PORT || "8080", 10);
const host = process.env.HOST || "0.0.0.0";
const server = createServer((req, res) => {
  if (req.url?.split("?")[0] === "/healthz") {
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(JSON.stringify({ ok: true, service: "Arbor3D", version: process.env.GITHUB_SHA || "local" }));
    return;
  }
  dispatch(req, res);
});

server.listen(port, host, () => {
  console.log(`Arbor3D listening on http://${host}:${port}`);
});

function shutdown() {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
