// Page side of browser Python. Two workers: "apps" serves the tutor and the project (via the service worker),
// "tests" runs tests and is replaced when code runs too long (the browser can't interrupt it otherwise).
const Python = (() => {
  const ROOT = new URL("../", document.baseURI).href;  // the site root: web/, store/, tests/, tutor/
  const BASE = new URL(".", document.baseURI).pathname; // where web/ lives on this host
  const TEST_LIMIT = 15000;

  function worker(role) {
    const w = { nextId: 0, waiting: new Map() };
    w.spawn = () => {
      w.worker = new Worker(new URL("python-worker.js", document.baseURI));
      w.worker.onmessage = e => {
        if (e.data.type === "run-tests") return runTestsFor(e.data);
        w.waiting.get(e.data.id)?.(e.data);
        w.waiting.delete(e.data.id);
      };
      w.ready = w.send("init", { role, root: ROOT, base: BASE });
      return w.ready;
    };
    w.send = (type, data = {}, timeout = 0) => new Promise((resolve, reject) => {
      const id = ++w.nextId;
      let timer;
      w.waiting.set(id, m => { clearTimeout(timer); m.ok ? resolve(m.value) : reject(new Error(m.error)); });
      if (timeout) timer = setTimeout(() => { w.waiting.delete(id); w.restart(); reject(new Error("timeout")); }, timeout);
      w.worker.postMessage({ id, type, ...data });
    });
    w.restart = () => {
      w.worker.terminate();
      for (const done of w.waiting.values()) done({ ok: false, error: "Python restarted" });
      w.waiting.clear();
      w.spawn();
    };
    return w;
  }

  const apps = worker("apps"), tests = worker("tests");

  async function runTestsFor({ id, test, overrides }) {
    let results;
    try {
      await tests.ready;
      results = await tests.send("tests", { test, overrides: JSON.parse(overrides) }, TEST_LIMIT);
    } catch (err) {
      results = [{ name: "time limit", passed: false, message: err.message === "timeout"
        ? `Your code ran for more than ${TEST_LIMIT / 1000} seconds. Is there a loop that never ends?`
        : "The tests couldn't run: " + err.message }];
    }
    apps.worker.postMessage({ type: "tests-done", testId: id, results: JSON.stringify(results) });
  }

  // Requests from the tutor and project frames, via the service worker.
  navigator.serviceWorker?.addEventListener("message", async e => {
    if (e.data?.type !== "http") return;
    try { await apps.ready; } catch {}
    apps.worker.postMessage({ type: "http", req: e.data.req, port: e.ports[0] }, [e.ports[0]]);
  });

  return {
    async start() {
      await navigator.serviceWorker.register(new URL("sw.js", document.baseURI));
      await navigator.serviceWorker.ready;
      tests.spawn();
      return apps.spawn();
    },
  };
})();
