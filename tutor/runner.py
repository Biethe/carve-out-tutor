"""Runs a piece's tests on the learner's code, and assembles and (re)starts the store."""
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

from tutor.pieces import PIECES

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RUN_DIR = ROOT / ".run" / "store"
STORE_PORT = 8001
STORE_URL = f"http://localhost:{STORE_PORT}"

_store_proc: subprocess.Popen | None = None
TEST_TIMEOUT = 15


def run_tests(piece: str, code: str) -> list[dict]:
    """Run the piece's tests against the learner's code in a separate process. Returns [{name, passed, message}]."""
    p = PIECES[piece]
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, p["file"]).write_text(code)
        report = Path(tmp, "report.xml")
        cmd = [sys.executable, "-m", "pytest", str(ROOT / p["test"]), f"--junitxml={report}", "-q", "-p", "no:cacheprovider"]
        try:
            # The temp folder comes first on PYTHONPATH, so the tests import the learner's file.
            out = subprocess.run(cmd, cwd=tmp, env={**os.environ, "PYTHONPATH": tmp},
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


def run_store(passed: list[str]) -> dict:
    """Copy the store, swap in the learner's passed pieces, restart it. Returns {"url"} or {"error"}."""
    global _store_proc
    stop_store()
    if _port_in_use(STORE_PORT):
        return {"error": f"Port {STORE_PORT} is already in use by another program. Close it and try again."}

    shutil.rmtree(RUN_DIR, ignore_errors=True)
    shutil.copytree(ROOT / "store", RUN_DIR, ignore=shutil.ignore_patterns("__pycache__", "*.db"))
    for piece in passed:
        shutil.copy(DATA / "learner" / f"{piece}.py", RUN_DIR / "pieces" / f"{piece}.py")

    DATA.mkdir(exist_ok=True)
    log_path = RUN_DIR.parent / "store.log"
    env = {**os.environ, "STORE_DB": str(DATA / "store.db")}
    with open(log_path, "w") as log:
        _store_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--port", str(STORE_PORT)],
            cwd=RUN_DIR, env=env, stdout=log, stderr=subprocess.STDOUT,
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
    return {"error": "The store couldn't start.", "output": tail}
