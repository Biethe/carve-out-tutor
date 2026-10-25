"""Runs a piece's tests on the learner's code, and assembles and (re)starts the store."""
import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from tutor import pieces
from tutor.pieces import PIECES
from tutor.progress import DATA

ROOT = Path(__file__).parent.parent
STORE_PORT = 8001
STORE_URL = f"http://localhost:{STORE_PORT}"

_store_proc: subprocess.Popen | None = None
TEST_TIMEOUT = 15


def test_source(piece: str, name: str) -> tuple[str, str]:
    """(file name, code) of the tests for one function: the piece's hand-written tests, or the AI-written ones."""
    if PIECES[piece]["test"]:
        path = ROOT / PIECES[piece]["test"]
        return path.name, path.read_text()
    from tutor import cards
    return cards.test_file(piece, name)


async def run_tests(piece: str, name: str, code: str) -> list[dict]:
    """Run the piece's tests against the learner's code in a separate process. Returns [{name, passed, message}].
    In the browser, web/bridge.py swaps this for a browser-Python worker."""
    return await run_test_code(PIECES[piece]["file"], *test_source(piece, name), code)


async def run_test_code(file: str, test_name: str, test_code: str, code: str) -> list[dict]:
    """Run one test file against the store with `file` replaced by `code`. In the browser, web/bridge.py swaps this."""
    return await asyncio.to_thread(_run_tests, file, test_name, test_code, code)


def _run_tests(file: str, test_name: str, test_code: str, code: str) -> list[dict]:
    """The tests run against a copy of the whole store with `file` (e.g. pieces/auth.py) replaced by `code`."""
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp, pieces.STORE.name)
        shutil.copytree(pieces.STORE, store, ignore=shutil.ignore_patterns("__pycache__", "*.db", ".git", "node_modules"))
        (store / file).write_text(code)
        Path(tmp, "tests").mkdir()
        shutil.copy(ROOT / "tests" / "conftest.py", Path(tmp, "tests"))
        Path(tmp, "tests", test_name).write_text(test_code)
        report = Path(tmp, "report.xml")
        cmd = [sys.executable, "-m", "pytest", str(Path(tmp, "tests", test_name)), f"--junitxml={report}", "-q", "-p", "no:cacheprovider"]
        try:
            out = subprocess.run(cmd, cwd=tmp, env={**os.environ, "STORE_DIR": str(store), "STORE_DB": str(Path(tmp, "store.db"))},
                                 capture_output=True, text=True, timeout=TEST_TIMEOUT)
        except subprocess.TimeoutExpired:
            return [{"name": "time limit", "passed": False,
                     "message": f"Your code ran for more than {TEST_TIMEOUT} seconds. Is there a loop that never ends?"}]
        cases = ET.parse(report).getroot().iter("testcase") if report.exists() else []
        results = []
        for case in cases:
            failure, error = case.find("failure"), case.find("error")
            if failure is not None:
                message = _short(failure.get("message") or "")
            elif error is not None:
                # Errors like a SyntaxError or bad import: the useful part is the end of the traceback.
                message = _short((error.text or error.get("message") or "").replace(tmp + "/", ""), lines=5, last=True)
            else:
                message = None
            results.append({"name": case.get("name"), "passed": message is None, "message": message})
        return results or [{"name": "running the tests", "passed": False, "message": _short(out.stdout + out.stderr)}]


def _short(text: str, lines: int = 12, last: bool = False) -> str:
    text_lines = text.strip().splitlines() or ["(no message)"]
    return "\n".join(text_lines[-lines:] if last else text_lines[:lines])


def _port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def stop_store():
    global _store_proc
    if _store_proc and _store_proc.poll() is None:
        _store_proc.terminate()
        try:
            _store_proc.wait(5)
        except subprocess.TimeoutExpired:
            _store_proc.kill()
            _store_proc.wait()
    _store_proc = None


STATIC_SHIM = """from starlette.staticfiles import StaticFiles
app = StaticFiles(directory={folder!r}, html=True)  # a plain web page, served as it is
"""


def run_store(passed: list[str]) -> dict:
    """Copy the active project, swap in the learner's passed pieces, (re)start it. Returns {"url"} or {"error"}.
    FastAPI/Starlette apps run as they are, Flask apps as WSGI, a plain web page is served as static files."""
    global _store_proc
    from tutor import projects, progress
    stop_store()
    root = pieces.STORE
    how = projects.kind(root)
    if how["kind"] == "tests":
        return {"error": "This project isn't a web app or a web page, so it's checked with tests only."}
    if _port_in_use(STORE_PORT):
        return {"error": f"Port {STORE_PORT} is already in use by another program. Close it and try again."}

    run_dir = ROOT / ".run" / root.name
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(root, run_dir, ignore=shutil.ignore_patterns("__pycache__", "*.db", ".git", "node_modules"))
    for piece in passed:
        shutil.copy(progress.work() / "learner" / PIECES[piece]["file"], run_dir / PIECES[piece]["file"])
    if how["kind"] == "static":
        (run_dir / "_carve_static.py").write_text(STATIC_SHIM.format(folder=how["folder"]))
        target = ["_carve_static:app"]
    else:
        target = [f"{how['module']}:{how['var']}"] + (["--interface", "wsgi"] if how["kind"] == "wsgi" else [])

    DATA.mkdir(exist_ok=True)
    log_path = run_dir.parent / f"{root.name}.log"
    env = {**os.environ, "STORE_DB": str(DATA / "store.db")}
    with open(log_path, "w") as log:
        _store_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", *target, "--port", str(STORE_PORT)],
            cwd=run_dir, env=env, stdout=log, stderr=subprocess.STDOUT,
        )

    deadline = time.time() + 10
    while time.time() < deadline:
        if _store_proc.poll() is not None:
            break  # crashed on startup
        try:
            urllib.request.urlopen(STORE_URL, timeout=1)
            return {"url": STORE_URL}
        except OSError:
            time.sleep(0.2)
    stop_store()
    tail = "\n".join(log_path.read_text().splitlines()[-15:])
    return {"error": "The project couldn't start. If it needs extra packages: pip install -r requirements.txt", "output": tail}
