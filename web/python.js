// Page side of browser Python: starts the worker, passes the service worker's requests to it,
// and stops code that runs too long by replacing the worker (the browser can't interrupt it otherwise).
const Python = (() => {
  const BASE = new URL("../", document.baseURI).href;   // the site root: web/, store/, tests/ live under it
  const PREFIX = new URL("run", document.baseURI).pathname;
  let worker, ready, nextId = 0, lastStart = null;
  const waiting = new Map();

  function spawn() {
    worker = new Worker(new URL("python-worker.js", document.baseURI));
    worker.onmessage = e => { waiting.get(e.data.id)?.(e.data); waiting.delete(e.data.id); };
    ready = send("init", { base: BASE, prefix: PREFIX }, 0);
    return ready;
  }

  function send(type, data = {}, timeout = 0) {
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      let timer;
      waiting.set(id, m => { clearTimeout(timer); m.ok ? resolve(m.value) : reject(new Error(m.error)); });
      if (timeout) timer = setTimeout(() => { waiting.delete(id); restart(); reject(new Error("timeout")); }, timeout);
      worker.postMessage({ id, type, ...data });
    });
  }

  function restart() {
    worker.terminate();
    for (const done of waiting.values()) done({ ok: false, error: "Python restarted" });
    waiting.clear();
    spawn().then(() => lastStart && send("start", lastStart));
  }

  // Requests from the project running in the frame, via the service worker.
  navigator.serviceWorker?.addEventListener("message", async e => {
    if (e.data?.type !== "http") return;
    await ready;
    worker.postMessage({ type: "http", req: e.data.req, port: e.ports[0] }, [e.ports[0]]);
  });

  async function start() {
    await navigator.serviceWorker.register(new URL("sw.js", document.baseURI));
    await navigator.serviceWorker.ready;
    return spawn();
  }

  return {
    start,
    // [{name, passed, message}]. Code that runs past the limit fails with a clear message.
    async tests(test, overrides, limit = 15000) {
      await ready;
      try {
        return await send("tests", { test, overrides }, limit);
      } catch (err) {
        if (err.message !== "timeout") throw err;
        return [{ name: "time limit", passed: false, message: `Your code ran for more than ${limit / 1000} seconds. Is there a loop that never ends?` }];
      }
    },
    // Loads the web app in app/ with the given files replaced; it's then served at run/.
    async run(app, overrides = {}) {
      await ready;
      lastStart = { app, overrides };
      await send("start", lastStart);
      return PREFIX + "/";
    },
  };
})();
