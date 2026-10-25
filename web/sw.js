// Service worker: requests under tutor/ and run/ go to web apps running in browser Python (the tutor itself,
// and the learner's project). It asks the main page, which owns Python, through a private message channel.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

const SCOPE = new URL(self.registration.scope).pathname;
const MOUNTS = ["tutor", "run"];

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  const mount = url.origin === location.origin && MOUNTS.find(m => url.pathname.startsWith(SCOPE + m + "/"));
  if (mount) e.respondWith(answer(e.request, url, mount));
});

async function answer(request, url, mount) {
  const pages = await self.clients.matchAll({ type: "window" });
  const main = pages.find(c => !MOUNTS.some(m => new URL(c.url).pathname.startsWith(SCOPE + m + "/")));
  if (!main) return new Response("Open the tutor's main page to run this.", { status: 503 });
  const req = {
    mount,
    method: request.method,
    path: "/" + url.pathname.slice((SCOPE + mount + "/").length),
    query: url.search.slice(1),
    headers: [...request.headers],
    body: await request.arrayBuffer(),
  };
  const channel = new MessageChannel();
  const reply = new Promise(resolve => (channel.port1.onmessage = m => resolve(m.data)));
  main.postMessage({ type: "http", req }, [channel.port2]);
  const { ok, value, error } = await reply;
  if (!ok) return new Response("Python crashed:\n\n" + error, { status: 500, headers: { "content-type": "text/plain" } });
  const location = value.headers.find(([k]) => k.toLowerCase() === "location");
  if (value.status >= 300 && value.status < 400 && location) return Response.redirect(new URL(location[1], url).href, value.status);
  const empty = value.status === 204 || value.status === 304;
  return new Response(empty ? null : value.body, { status: value.status, headers: value.headers });
}
