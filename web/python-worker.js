// Browser Python in a Web Worker, so the page never freezes. Two roles, one worker each:
// "tests" runs test files (the page replaces this worker when code runs too long);
// "apps" serves the tutor and the learner's project, and saves the tutor's data in IndexedDB.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.js");

let py, bridge, role;
const DATA = "/persist/data";

async function boot(data) {
  role = data.role;
  py = await loadPyodide();
  // Both need the store's libraries: tests can import the store's web app and database too.
  await py.loadPackage(["micropip", "jinja2", "sqlite3", "pydantic", ...(role === "tests" ? ["pytest"] : [])]);
  await py.pyimport("micropip").install(["fastapi", "python-multipart", "itsdangerous"]);
  const files = await (await fetch(data.root + "web/files.json")).json();
  await Promise.all(files.map(async path => {
    const bytes = new Uint8Array(await (await fetch(data.root + path)).arrayBuffer());
    py.FS.mkdirTree("/project/" + path.split("/").slice(0, -1).join("/"));
    py.FS.writeFile("/project/" + path, bytes);
  }));
  py.FS.mkdirTree("/bridge");
  py.FS.writeFile("/bridge/bridge.py", await (await fetch(data.root + "web/bridge.py")).text());
  py.runPython("import sys; sys.path.insert(0, '/bridge')");
  bridge = py.pyimport("bridge");
  if (role === "apps") {
    py.FS.mkdirTree("/persist");
    py.FS.mount(py.FS.filesystems.IDBFS, {}, "/persist");
    await sync(true);
    py.FS.mkdirTree(DATA);
    bridge.setup_apps(data.base, DATA);
    bridge.start_tutor();
  }
}

// Installs packages with micropip once per worker. A package that can't install is skipped: its tests will say so.
const installed = new Set();
async function installOnce(names) {
  const todo = names.filter(n => !installed.has(n));
  todo.forEach(n => installed.add(n));
  for (const name of todo) { try { await py.pyimport("micropip").install(name); } catch {} }
}

// IndexedDB <-> /persist. `load` reads saved data in; otherwise writes changes out.
const sync = load => new Promise((ok, fail) => py.FS.syncfs(load, err => (err ? fail(err) : ok())));

// The tutor asks for tests through the page, which owns the tests worker and its time limit.
let nextTest = 0;
const testReplies = new Map();
self.runTests = job => new Promise(resolve => {
  const id = ++nextTest;
  testReplies.set(id, resolve);
  postMessage({ type: "run-tests", id, job });
});

const handlers = {
  init: data => boot(data).then(() => ({ ready: true })),
  tests: async ({ job }) => {
    if (job.requirements?.length) await installOnce(job.requirements);  // an uploaded project's own packages
    return JSON.parse(bridge.run_tests(job.file, job.test_name, job.test_code, job.code, job.project || "store",
                                       job.files ? JSON.stringify(job.files) : ""));
  },
  "tests-done": ({ testId, results }) => { testReplies.get(testId)?.(results); testReplies.delete(testId); },
  http: async ({ req }) => {
    const res = await bridge.handle(req.mount, req.method, req.path, req.query, JSON.stringify(req.headers), new Uint8Array(req.body));
    const out = res.toJs({ dict_converter: Object.fromEntries });
    res.destroy();
    if (req.method !== "GET") await sync(false);
    return { status: out.status, headers: out.headers, body: out.body };
  },
};

onmessage = async e => {
  const reply = e.data.port || self;
  try {
    const value = await handlers[e.data.type](e.data);
    if (e.data.id !== undefined || e.data.port) reply.postMessage({ id: e.data.id, ok: true, value });
  } catch (err) {
    reply.postMessage({ id: e.data.id, ok: false, error: String(err.message || err) });
  }
};
