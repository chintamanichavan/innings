// Keeps fonts and icons on the device, so a repeat visit paints at once.
// Pages and data always come fresh from the network.

const CACHE = "innings-assets-3";
const KEPT_ON_DEVICE = /^\/(fonts\/|icon)/;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  const dropOldCaches = caches.keys().then((names) => (
    Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name)))
  ));
  event.waitUntil(dropOldCaches.then(() => self.clients.claim()));
});

async function fromCacheOrNetwork(request) {
  const cache = await caches.open(CACHE);
  const kept = await cache.match(request);
  if (kept) return kept;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const ours = event.request.method === "GET" && url.origin === location.origin;
  if (ours && KEPT_ON_DEVICE.test(url.pathname)) event.respondWith(fromCacheOrNetwork(event.request));
});
