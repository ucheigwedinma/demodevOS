import { build, files, prerendered, version } from "$service-worker";

const CACHE_NAME = `developeros-cache-${version}`;
const PRECACHE_URLS = [...build, ...files, ...prerendered];
const PRECACHE_SET = new Set(PRECACHE_URLS);
const IS_LOCALHOST =
  self.location.hostname === "localhost"
  || self.location.hostname === "127.0.0.1";
const SCOPE_PATH = (() => {
  try {
    const scope = new URL(self.registration.scope).pathname.replace(/\/$/, "");
    return scope === "/" ? "" : scope;
  } catch {
    return "";
  }
})();

function withScope(path) {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!SCOPE_PATH) return normalized;
  return `${SCOPE_PATH}${normalized}`.replace(/\/{2,}/g, "/");
}

const BYPASS_PREFIXES = ["/api/", "/media/", "/login", "/logout", "/auth/"];

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok) {
    await cache.put(request, response.clone());
  }
  return response;
}

async function networkFirstWithFallback(request) {
  const cache = await caches.open(CACHE_NAME);

  try {
    const response = await fetch(request);
    if (response.ok && !response.redirected && response.type !== "opaqueredirect") {
      await cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;

    const appShell =
      (await cache.match(withScope("/"))) ??
      (await cache.match(withScope("/index.html"))) ??
      (await cache.match("/index.html"));

    if (appShell) return appShell;

    return new Response("Offline", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const networkPromise = fetch(request)
    .then(async (response) => {
      if (response.ok) {
        await cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);

  if (cached) {
    return cached;
  }

  const network = await networkPromise;
  if (network) return network;

  return new Response("Offline", {
    status: 503,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

self.addEventListener("install", (event) => {
  if (IS_LOCALHOST) {
    event.waitUntil(self.skipWaiting());
    return;
  }
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      await cache.addAll(PRECACHE_URLS);
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => IS_LOCALHOST ? key.startsWith("developeros-cache-") : key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  if (IS_LOCALHOST) return;
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (BYPASS_PREFIXES.some((p) => url.pathname.startsWith(p))) return;

  if (PRECACHE_SET.has(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstWithFallback(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});
