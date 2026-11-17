const VERSION = "arbor3d-v3";
const SHELL_CACHE = `${VERSION}-shell`;
const RUNTIME_CACHE = `${VERSION}-runtime`;
const SHELL = ["/", "/manifest.webmanifest", "/favicon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key)),
    )),
  );
  self.clients.claim();
});

async function trim(cache, maximum = 300) {
  const keys = await cache.keys();
  await Promise.all(keys.slice(0, Math.max(0, keys.length - maximum)).map((key) => cache.delete(key)));
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok || response.type === "opaque") {
    const cache = await caches.open(RUNTIME_CACHE);
    await cache.put(request, response.clone());
    await trim(cache);
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return;

  // Published analysis changes without rebuilding the App. Prefer the new result,
  // retaining the most recently fetched snapshot only for an offline visit.
  if (url.origin === self.location.origin && url.pathname.startsWith('/analysis/')) {
    event.respondWith((async () => {
      const cache = await caches.open(RUNTIME_CACHE);
      const key = url.origin + url.pathname;
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put(key, response.clone());
        return response;
      } catch (error) {
        const cached = await cache.match(key);
        if (cached) return cached;
        throw error;
      }
    })());
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(async (response) => {
          const cache = await caches.open(SHELL_CACHE);
          await cache.put("/", response.clone());
          return response;
        })
        .catch(() => caches.match("/")),
    );
    return;
  }

  if (
    ["script", "style", "image", "font"].includes(request.destination) ||
    url.pathname.endsWith(".json")
  ) {
    event.respondWith(cacheFirst(request));
  }
});
