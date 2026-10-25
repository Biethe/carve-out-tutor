// Browser Python in a Web Worker, so the page never freezes. Loads the project files listed in files.json,
// then answers messages: {type: "tests" | "start" | "http"}. Replies go to e.data.port when given, else to the page.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.js");

let py, bridge;

async function boot(base, prefix) {
  py = await loadPyodide();
  await py.loadPackage(["micropip", "pytest", "jinja2", "sqlite3", "pydantic"]);
  await py.pyimport("micropip").install(["fastapi", "python-multipart", "itsdangerous"]);
  const files = await (await fetch(base + "web/files.json")).json();
  await Promise.all(files.map(async path => {
    const bytes = new Uint8Array(await (await fetch(base + path)).arrayBuffer());
    py.FS.mkdirTree("/project/" + path.split("/").slice(0, -1).join("/"));
    py.FS.writeFile("/project/" + path, bytes);
  }));
  py.FS.mkdirTree("/bridge");
  py.FS.writeFile("/bridge/bridge.py", await (await fetch(base + "web/bridge.py")).text());
  py.runPython("import sys; sys.path.insert(0, '/bridge')");
  bridge = py.pyimport("bridge");
  bridge.setup(prefix);
}

const handlers = {
  init: ({ base, prefix }) => boot(base, prefix).then(() => ({ ready: true })),
  tests: ({ test, overrides }) => bridge.run_tests(test, py.toPy(overrides || {})).toJs({ dict_converter: Object.fromEntries }),
  start: ({ app, overrides }) => { bridge.start_app(app, py.toPy(overrides || {})); return { started: true }; },
  http: async ({ req }) => {
    const res = await bridge.handle(req.method, req.path, req.query, py.toPy(req.headers), py.toPy(new Uint8Array(req.body)));
    const out = res.toJs({ dict_converter: Object.fromEntries });
    res.destroy();
    return { status: out.status, headers: out.headers, body: out.body };
  },
};

onmessage = async e => {
  const reply = e.data.port || self;
  try {
    reply.postMessage({ id: e.data.id, ok: true, value: await handlers[e.data.type](e.data) });
  } catch (err) {
    reply.postMessage({ id: e.data.id, ok: false, error: String(err.message || err) });
  }
};
