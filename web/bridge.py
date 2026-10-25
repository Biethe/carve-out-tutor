"""Runs inside browser Python (Pyodide). Two jobs, one per worker:
- tests worker: run_tests() runs a project's test file with some files replaced;
- app worker: serves web apps with no server. The tutor itself is mounted at tutor/, the learner's project at run/.
The page's JavaScript calls these functions; everything here is plain Python."""
import json
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("/project")      # the site's files: store/, tests/, tutor/
RUNNING = Path("/running")   # copies of apps with the learner's files swapped in
BASE = ""                    # the site's path on its host, e.g. /repo/web
_apps: dict = {}
_cookies: dict[str, dict[str, str]] = {}


# ---- Tests ---------------------------------------------------------------------

def _forget(folders: tuple[str, ...]):
    """Drop modules loaded from these folders, so the next import reads the files as they are now."""
    for name, mod in list(sys.modules.items()):
        if (getattr(mod, "__file__", None) or "").startswith(folders) or name.startswith(("test_", "conftest")):
            del sys.modules[name]


def _short(text: str, lines: int = 12, last: bool = False) -> str:
    text_lines = text.strip().splitlines() or ["(no message)"]
    return "\n".join(text_lines[-lines:] if last else text_lines[:lines])


def run_tests(file: str, test_name: str, test_code: str, code: str, project: str = "store", files_json: str = "") -> str:
    """Run one test file against a copy of the project with `file` replaced by `code`, as tutor/runner.py does locally.
    The built-in store is here already; an uploaded project's files come with the job. Returns the results as JSON."""
    import pytest

    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp, project)
        if files_json:
            for rel, text in json.loads(files_json).items():
                (store / rel).parent.mkdir(parents=True, exist_ok=True)
                (store / rel).write_text(text)
        else:
            shutil.copytree(ROOT / "store", store, ignore=shutil.ignore_patterns("__pycache__", "*.db"))
        (store / file).write_text(code)
        Path(tmp, "tests").mkdir()
        shutil.copy(ROOT / "tests" / "conftest.py", Path(tmp, "tests"))
        Path(tmp, "tests", test_name).write_text(test_code)
        report = Path(tmp, "report.xml")
        os.environ.update(STORE_DIR=str(store), STORE_DB=str(Path(tmp, "store.db")))
        folders = (str(ROOT), tmp)
        _forget(folders)
        saved_path = list(sys.path)
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            pytest.main([str(Path(tmp, "tests", test_name)), f"--junitxml={report}", "-q", "-p", "no:cacheprovider"])
        finally:
            os.chdir(cwd)
            sys.path[:] = saved_path
            _forget(folders)
        cases = ET.parse(report).getroot().iter("testcase") if report.exists() else []
        results = []
        for case in cases:
            failure, error = case.find("failure"), case.find("error")
            if failure is not None:
                message = _short(failure.get("message") or "")
            elif error is not None:
                message = _short((error.text or error.get("message") or "").replace(tmp + "/", ""), lines=5, last=True)
            else:
                message = None
            results.append({"name": case.get("name"), "passed": message is None, "message": message})
        return json.dumps(results or [{"name": "running the tests", "passed": False, "message": "The tests didn't run."}])


# ---- Web apps ------------------------------------------------------------------

def setup_apps(base: str, data: str):
    """Called once in the app worker, before any app is imported."""
    global BASE
    BASE = base.rstrip("/")
    os.environ["TUTOR_DATA"] = data
    os.environ["STORE_DB"] = f"{data}/store.db"
    import anyio.to_thread

    async def same_thread(func, *args, **_):
        return func(*args)

    # The browser has no threads. FastAPI runs plain `def` routes and file reads "in a thread"; here they just run.
    anyio.to_thread.run_sync = same_thread
    sys.path.insert(0, str(ROOT))


def start_tutor():
    import tutor.app
    from tutor import runner
    runner.run_test_code, runner.run_store, runner.stop_store = _browser_tests, _browser_store, lambda: None
    _apps["tutor"] = tutor.app.app


async def _browser_tests(file: str, test_name: str, test_code: str, code: str) -> list[dict]:
    """The tutor's runner, in the browser: the page runs the tests in the separate tests worker.
    An uploaded project lives only in this worker's storage, so its files travel with the job."""
    from js import runTests
    from tutor import pieces, projects
    job = {"file": file, "test_name": test_name, "test_code": test_code, "code": code, "project": pieces.STORE.name}
    if pieces.STORE != pieces.BUILTIN:
        job["files"] = {str(p.relative_to(pieces.STORE)): p.read_text(errors="replace") for p in pieces.STORE.rglob("*")
                        if p.is_file() and p.suffix in (".py", ".txt", ".html", ".json", ".cfg", ".toml", ".ini", ".csv", ".sql")}
        job["requirements"] = projects.requirements(pieces.STORE)
    return json.loads(await runTests(json.dumps(job)))


async def _browser_store(passed: list[str]) -> dict:
    """Run project, in the browser: the active project starts in this worker and is served at run/."""
    from tutor import pieces, progress, projects
    from tutor.pieces import PIECES
    how = projects.kind(pieces.STORE)
    if how["kind"] == "tests":
        return {"error": "This project isn't a web app or a web page, so it's checked with tests only."}
    try:
        needs = projects.requirements(pieces.STORE)
        if needs:
            import micropip
            await micropip.install(needs)
        start_app("run", pieces.STORE, how, {PIECES[p]["file"]: (progress.work() / "learner" / PIECES[p]["file"]).read_text() for p in passed})
    except Exception as err:
        return {"error": "The project couldn't start in the browser.", "output": _short(repr(err), last=True)}
    return {"url": f"{BASE}/run/"}


_wsgi_apps: set = set()  # mounts whose app is WSGI (Flask)


def start_app(mount: str, root: Path, how: dict, overrides: dict):
    """(Re)load a project's web app from a fresh copy with the learner's files swapped in.
    how: {"kind": "asgi"/"wsgi", "module", "var"} or {"kind": "static", "folder"} (see tutor/projects.py)."""
    copy = RUNNING / mount / root.name
    _forget((str(RUNNING / mount),))
    shutil.rmtree(RUNNING / mount, ignore_errors=True)
    shutil.copytree(root, copy, ignore=shutil.ignore_patterns("__pycache__", "*.db", ".git", "node_modules"))
    for path, code in overrides.items():
        (copy / path).write_text(code)
    _wsgi_apps.discard(mount)
    _cookies[mount] = {}
    if how["kind"] == "static":
        from starlette.staticfiles import StaticFiles
        _apps[mount] = StaticFiles(directory=str(copy / how["folder"]), html=True)
        return
    sys.path[:] = [p for p in sys.path if not p.startswith(str(RUNNING))]
    sys.path.insert(0, str(copy))
    cwd = os.getcwd()
    os.chdir(copy)
    try:
        import importlib
        module = importlib.import_module(how["module"])
    finally:
        os.chdir(cwd)
    _apps[mount] = getattr(module, how["var"])
    if how["kind"] == "wsgi":
        _wsgi_apps.add(mount)


def _call_wsgi(app, method: str, path: str, query: str, headers: list, body: bytes) -> dict:
    """A Flask (WSGI) app answers one request. Plain and synchronous: the browser has no threads."""
    import io
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path or "/", "QUERY_STRING": query, "SCRIPT_NAME": "",
               "SERVER_NAME": "app", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1", "wsgi.version": (1, 0),
               "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(body), "wsgi.errors": sys.stderr,
               "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": False, "CONTENT_LENGTH": str(len(body))}
    for k, v in headers:
        key = k.upper().replace("-", "_")
        environ[key if key in ("CONTENT_TYPE", "CONTENT_LENGTH") else "HTTP_" + key] = v
    sent = {}

    def start_response(status, response_headers, exc_info=None):
        sent["status"], sent["headers"] = int(status.split()[0]), list(response_headers)
        return lambda data: None

    result = app(environ, start_response)
    try:
        sent["body"] = b"".join(result)
    finally:
        getattr(result, "close", lambda: None)()
    return sent


def _remember_cookies(jar: dict, headers: list[tuple[str, str]]):
    for name, value in headers:
        if name.lower() != "set-cookie":
            continue
        pair, _, attrs = value.partition(";")
        key, _, val = pair.strip().partition("=")
        if "max-age=0" in attrs.lower() or "1970" in attrs or val in ("", "null"):
            jar.pop(key, None)
        else:
            jar[key] = val


# Addresses starting with / would leave the page's own path on the host, so they're moved under the mount.
# In HTML that's any quoted root path ("/move/1/2", or '/reset' inside an onclick), not just href/src/action,
# plus a bare root link (href="/"). A lone "/" in a script, like split("/"), is left alone.
_QUOTED_PATH = re.compile(r"""(["'])/(?=[\w\-.~%])""")
_ROOT_LINK = re.compile(r"""(=\s*["'])/(["'])""")
_CSS_URL = re.compile(r"""(url\(["']?)/(?!/)""")


async def handle(mount: str, method: str, path: str, query: str, headers_json: str, body: bytes) -> dict:
    """One browser request, answered by the app directly as ASGI. Links starting with / move under the mount."""
    app = _apps.get(mount)
    if app is None:
        return {"status": 404, "headers": [("content-type", "text/plain")], "body": b"Nothing is running here yet. Click Run project."}
    prefix = f"{BASE}/{mount}"
    jar = _cookies.setdefault(mount, {})
    headers = [(k, v) for k, v in json.loads(headers_json) if k.lower() != "cookie"]
    if jar:
        headers.append(("cookie", "; ".join(f"{k}={v}" for k, v in jar.items())))
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path or "/", "raw_path": (path or "/").encode(),
        "query_string": query.encode(), "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
        "server": ("app", 80), "client": ("browser", 0),
    }
    if mount in _wsgi_apps:
        sent = _call_wsgi(app, method, path, query, headers, bytes(body))
    else:
        sent = await _call_asgi(app, scope, bytes(body))
    return _finish(sent, jar, prefix)


async def _call_asgi(app, scope: dict, body: bytes) -> dict:
    sent = {"body": b""}
    chunks = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        return chunks.pop(0) if chunks else {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            sent["status"] = message["status"]
            sent["headers"] = [(k.decode(), v.decode()) for k, v in message.get("headers", [])]
        elif message["type"] == "http.response.body":
            sent["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return sent


def _finish(sent: dict, jar: dict, prefix: str) -> dict:
    """Keeps the cookies, and moves links starting with / under the mount."""
    _remember_cookies(jar, sent["headers"])
    out_headers, body = [], sent["body"]
    for k, v in sent["headers"]:
        if k.lower() == "set-cookie":
            continue
        if k.lower() == "location" and v.startswith("/"):
            v = prefix + v
        out_headers.append((k, v))
    kind = dict((k.lower(), v) for k, v in out_headers).get("content-type", "")
    if "text/html" in kind or "text/css" in kind:
        text = _CSS_URL.sub(rf"\1{prefix}/", body.decode("utf-8", "replace"))
        if "text/html" in kind:
            text = _ROOT_LINK.sub(rf"\1{prefix}/\2", _QUOTED_PATH.sub(rf"\1{prefix}/", text))
        body = text.encode()
        out_headers = [(k, v) for k, v in out_headers if k.lower() != "content-length"]
    return {"status": sent["status"], "headers": out_headers, "body": body}
