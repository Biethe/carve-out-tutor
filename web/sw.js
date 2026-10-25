// Service worker: every request under run/ goes to the project's web app running in browser Python.
// It asks the tutor page (which owns the Python worker) to answer, through a private message channel.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

const RUN = new URL("run/", self.registration.scope).pathname;

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.origin === location.origin && url.pathname.startsWith(RUN)) e.respondWith(answer(e.request, url));
});

async function answer(request, url) {
  const pages = await self.clients.matchAll({ type: "window" });
  const tutor = pages.find(c => !new URL(c.url).pathname.startsWith(RUN));
  if (!tutor) return new Response("Open the tutor page to run the project.", { status: 503 });
  const req = {
    method: request.method,
    path: "/" + url.pathname.slice(RUN.length),
    query: url.search.slice(1),
    headers: [...request.headers],
    body: await request.arrayBuffer(),
  };
  const channel = new MessageChannel();
  const reply = new Promise(resolve => (channel.port1.onmessage = m => resolve(m.data)));
  tutor.postMessage({ type: "http", req }, [channel.port2]);
  const { ok, value, error } = await reply;
  if (!ok) return new Response("The project crashed:\n\n" + error, { status: 500, headers: { "content-type": "text/plain" } });
  const location = value.headers.find(([k]) => k.toLowerCase() === "location");
  if (value.status >= 300 && value.status < 400 && location) return Response.redirect(new URL(location[1], url).href, value.status);
  return new Response(value.body, { status: value.status, headers: value.headers });
}
