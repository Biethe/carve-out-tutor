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
        if (e.data.type === "run-js") return runJsFor(e.data);
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

  async function runTestsFor({ id, job }) {
    let results;
    try {
      await tests.ready;
      results = await tests.send("tests", { job: JSON.parse(job) }, TEST_LIMIT);
    } catch (err) {
      results = [{ name: "time limit", passed: false, message: err.message === "timeout"
        ? `Your code ran for more than ${TEST_LIMIT / 1000} seconds. Is there a loop that never ends?`
        : "The tests couldn't run: " + err.message }];
    }
    apps.worker.postMessage({ type: "tests-done", testId: id, results: JSON.stringify(results) });
  }

  // JavaScript and TypeScript checks (tutor/langs.py): the project's files become modules, the entry file runs in a
  // fresh worker that only collects what it prints, and the worker is ended after the time limit.
  let typescript = null;
  const loadTypescript = () => typescript ||= new Promise((ok, fail) => {
    const script = Object.assign(document.createElement("script"), { src: "https://cdn.jsdelivr.net/npm/typescript@5.6.3/lib/typescript.js" });
    script.onload = () => ok(window.ts);
    script.onerror = () => { typescript = null; fail(new Error("TypeScript couldn't load. Check your connection.")); };
    document.head.append(script);
  });
  const WORKER = `const lines = [];
const text = (x) => { if (typeof x === "string") return x; try { return JSON.stringify(x); } catch { return String(x); } };
console.log = console.info = console.warn = console.error = (...a) => lines.push(a.map(text).join(" "));
globalThis.module = { exports: {} }; globalThis.exports = globalThis.module.exports;
globalThis.require = (name) => { throw new Error("require('" + name + "') isn't available in the browser version"); };
onmessage = async (e) => {
  try { await import(e.data); postMessage({ ok: true, out: lines.join("\\n") }); }
  catch (err) { postMessage({ ok: false, out: lines.join("\\n"), error: String((err && err.stack) || err) }); }
};`;

  async function runJs({ files, entry, lang, timeout }) {
    const ts = lang === "typescript" ? await loadTypescript() : null;
    const urls = new Map();
    const made = [];
    const find = (path) => [path, path.replace(/\.js$/, ".ts"), path + ".ts", path + ".js", path + ".mjs", path + "/index.ts", path + "/index.js"].find((p) => p in files);
    const join = (from, spec) => {
      const parts = from.split("/").slice(0, -1);
      for (const part of spec.split("/")) part === ".." ? parts.pop() : part !== "." && parts.push(part);
      return parts.join("/");
    };
    function url(path, stack) {
      if (urls.has(path)) return urls.get(path);
      let code = files[path];
      if (ts && /\.ts$/.test(path)) code = ts.transpileModule(code, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
      code = code.replace(/(\bfrom\s*|\bimport\s*\(?\s*)(["'])([^"']+)\2/g, (all, head, q, spec) => {
        if (/^(https?:|data:|blob:)/.test(spec)) return all;
        if (!spec.startsWith(".")) return head + q + "https://cdn.jsdelivr.net/npm/" + spec + "/+esm" + q;
        const target = find(join(path, spec));
        return target && !stack.includes(target) ? head + q + url(target, [...stack, path]) + q : all;
      });
      const href = URL.createObjectURL(new Blob([code], { type: "text/javascript" }));
      made.push(href);
      urls.set(path, href);
      return href;
    }
    const worker = new Worker(URL.createObjectURL(new Blob([WORKER], { type: "text/javascript" })), { type: "module" });
    try {
      return await new Promise((resolve) => {
        const timer = setTimeout(() => resolve({ ok: false, error: `It ran for more than ${timeout / 1000} seconds. Is there a loop that never ends?` }), timeout);
        worker.onmessage = (e) => { clearTimeout(timer); resolve(e.data); };
        worker.onerror = (e) => { clearTimeout(timer); resolve({ ok: false, error: e.message || "The code couldn't load." }); };
        worker.postMessage(url(entry, []));
      });
    } finally {
      worker.terminate();
      made.forEach(URL.revokeObjectURL);
    }
  }

  async function runJsFor({ id, job }) {
    let reply;
    try { reply = await runJs(JSON.parse(job)); } catch (err) { reply = { ok: false, error: err.message }; }
    apps.worker.postMessage({ type: "js-done", testId: id, results: JSON.stringify(reply) });
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
