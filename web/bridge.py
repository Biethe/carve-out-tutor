"""Runs inside browser Python (Pyodide): the project's tests, and the project's web app with no server.
The page's JavaScript calls run_tests() and handle(); everything here is plain Python."""
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import anyio.to_thread

ROOT = Path("/project")
PREFIX = ""  # where the app is served in the page, e.g. /web/run (set by setup)
_app = None
_cookies: dict[str, str] = {}


async def _same_thread(func, *args, **_):
    return func(*args)


# The browser has no threads. FastAPI runs plain `def` routes and file reads "in a thread"; here they just run.
anyio.to_thread.run_sync = _same_thread


def setup(prefix: str):
    global PREFIX
    PREFIX = prefix.rstrip("/")
    os.environ["STORE_DB"] = "/data/store.db"


def _forget_project_modules():
    """Drop the project's modules so the next import reads the files as they are now."""
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, "__file__", None) or ""
        if path.startswith((str(ROOT), tempfile.gettempdir())) or name.startswith(("test_", "conftest")):
            del sys.modules[name]


def _short(text: str, lines: int = 12, last: bool = False) -> str:
    text_lines = text.strip().splitlines() or ["(no message)"]
    return "\n".join(text_lines[-lines:] if last else text_lines[:lines])


def run_tests(test_file: str, overrides: dict) -> list[dict]:
    """Run one test file with some project files replaced. Same result shape as tutor/runner.py."""
    import pytest

    with tempfile.TemporaryDirectory() as tmp:
        for path, code in overrides.items():
            Path(tmp, Path(path).name).write_text(code)  # tests import pieces by bare name, like the local runner
        report = Path(tmp, "report.xml")
        sys.path.insert(0, tmp)
        _forget_project_modules()
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            pytest.main([str(ROOT / test_file), f"--junitxml={report}", "-q", "-p", "no:cacheprovider"])
        finally:
            os.chdir(cwd)
            sys.path.remove(tmp)
            _forget_project_modules()
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
        return results or [{"name": "running the tests", "passed": False, "message": "The tests didn't run."}]


def start_app(app_dir: str, overrides: dict):
    """(Re)load the web app from the project files, with the learner's passed files swapped in."""
    global _app
    for path, code in overrides.items():
        (ROOT / path).write_text(code)
    _forget_project_modules()
    Path("/data").mkdir(exist_ok=True)
    sys.path[:] = [p for p in sys.path if not p.startswith(str(ROOT))]
    sys.path.insert(0, str(ROOT / app_dir))
    cwd = os.getcwd()
    os.chdir(ROOT / app_dir)
    try:
        import app as module
    finally:
        os.chdir(cwd)
    _app = module.app
    _cookies.clear()


def _remember_cookies(headers: list[tuple[str, str]]):
    for name, value in headers:
        if name.lower() != "set-cookie":
            continue
        pair, _, attrs = value.partition(";")
        key, _, val = pair.strip().partition("=")
        gone = "max-age=0" in attrs.lower() or "1970" in attrs or val in ("", "null")
        if gone:
            _cookies.pop(key, None)
        else:
            _cookies[key] = val


_LINK = re.compile(r"""((?:href|src|action)=["'])/(?!/)""")
_CSS_URL = re.compile(r"""(url\(["']?)/(?!/)""")


async def handle(method: str, path: str, query: str, headers: list, body: bytes) -> dict:
    """One browser request, answered by the app directly as ASGI. Links starting with / are moved under PREFIX."""
    headers = [(k, v) for k, v in headers if k.lower() != "cookie"]
    if _cookies:
        headers.append(("cookie", "; ".join(f"{k}={v}" for k, v in _cookies.items())))
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path or "/", "raw_path": (path or "/").encode(),
        "query_string": query.encode(), "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
        "server": ("app", 80), "client": ("browser", 0),
    }
    sent = {"body": b""}
    chunks = [{"type": "http.request", "body": bytes(body), "more_body": False}]

    async def receive():
        return chunks.pop(0) if chunks else {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            sent["status"] = message["status"]
            sent["headers"] = [(k.decode(), v.decode()) for k, v in message.get("headers", [])]
        elif message["type"] == "http.response.body":
            sent["body"] += message.get("body", b"")

    await _app(scope, receive, send)
    _remember_cookies(sent["headers"])
    out_headers, body = [], sent["body"]
    for k, v in sent["headers"]:
        if k.lower() == "set-cookie":
            continue
        if k.lower() == "location" and v.startswith("/"):
            v = PREFIX + v
        out_headers.append((k, v))
    kind = dict((k.lower(), v) for k, v in out_headers).get("content-type", "")
    if "text/html" in kind or "text/css" in kind:
        text = body.decode("utf-8", "replace")
        text = _CSS_URL.sub(rf"\1{PREFIX}/", _LINK.sub(rf"\1{PREFIX}/", text))
        body = text.encode()
        out_headers = [(k, v) for k, v in out_headers if k.lower() != "content-length"]
    return {"status": sent["status"], "headers": out_headers, "body": body}
