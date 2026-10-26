"""Uploaded projects: unpacked from a zip into data/uploads/<name>/, checked for harmful code before anything runs,
and downloaded back as a zip with the learner's passed functions inside. Polyvault (store/) is the built-in one."""
import io
import json
import re
import zipfile
from pathlib import Path

from tutor import langs, pieces, progress
from tutor.pieces import PIECES, assemble

UPLOADS = progress.DATA / "uploads"
ACTIVE = progress.DATA / "active.json"
MAX_BYTES = 20_000_000  # unpacked
MAX_FILES = 2000
JUNK = {"__pycache__", ".git", "node_modules", "venv", ".venv", "env", ".idea", ".vscode", "dist", "build", "__MACOSX"}


def slug(name: str) -> str:
    """A folder-safe name. A GitHub download's "-main"/"-master" suffix is dropped."""
    name = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")
    return re.sub(r"-(main|master)$", "", name)[:40] or "project"


def unpack(filename: str, data: bytes) -> tuple[str | None, str | None]:
    """Unpacks an uploaded zip. Returns (project name, None), or (None, why it was refused)."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None, "That isn't a zip file."
    entries = [e for e in archive.infolist() if not e.is_dir() and not JUNK & set(Path(e.filename).parts)]
    if len(entries) > MAX_FILES or sum(e.file_size for e in entries) > MAX_BYTES:
        return None, f"That project is too big (over {MAX_FILES} files or {MAX_BYTES // 1_000_000} MB unpacked)."
    if any(Path(e.filename).is_absolute() or ".." in Path(e.filename).parts for e in entries):
        return None, "That zip has file paths that point outside its own folder, so it can't be opened."
    # A GitHub download wraps everything in one top folder (repo-main/): leave it out.
    tops = {Path(e.filename).parts[0] for e in entries}
    strip = len(tops) == 1 and all(len(Path(e.filename).parts) > 1 for e in entries)
    names = [str(Path(*Path(e.filename).parts[1:])) if strip else e.filename for e in entries]
    if not any(langs.lang(n) for n in names):
        return None, ("There's no code Carve-Out can read in that zip. It reads Python, JavaScript, TypeScript, Java, "
                      "C, C++, Rust, SQL, HTML and CSS.")
    name = slug(next(iter(tops)) if strip else filename)
    if name == "store":
        name = "store-upload"
    root = UPLOADS / name
    if root.exists():
        import shutil
        shutil.rmtree(root)
    for entry, rel in zip(entries, names):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(entry))
    return name, None


GITHUB = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/([^?#]+?))?/?(?:[?#].*)?$")
FETCH_FILES = 600  # files fetched one by one from GitHub: enough for a big project, quick enough to wait for


async def _get(url: str) -> bytes:
    """GET a URL. In the browser this is the page's fetch: GitHub's API and raw files allow it (its zips don't)."""
    import sys
    if sys.platform == "emscripten":
        from pyodide.http import pyfetch
        reply = await pyfetch(url)
        if not reply.ok:
            raise RuntimeError(str(reply.status))
        return await reply.bytes()
    import asyncio
    import urllib.error
    import urllib.request

    def get():
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "carve-out-tutor"}), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as err:
            raise RuntimeError(str(err.code)) from None
    return await asyncio.to_thread(get)


async def from_github(url: str) -> tuple[bytes | None, str]:
    """A public GitHub repository as zip bytes, fetched file by file, so it goes through the same checks as an
    upload. Returns (zip, its file name) or (None, why not)."""
    import asyncio
    found = GITHUB.search(url.strip())
    if not found:
        return None, "That doesn't look like a GitHub project link. It should look like github.com/owner/project."
    owner, repo, ref = found[1], found[2], found[3] or "HEAD"
    try:
        tree = json.loads(await _get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"))
    except Exception as err:
        return None, ("GitHub says that project doesn't exist, or it's private." if "404" in str(err) or "422" in str(err)
                      else "GitHub is limiting requests from this network right now (60 an hour). Try again later, or download the zip and drop it here."
                      if "403" in str(err) or "429" in str(err) else "GitHub couldn't be reached. Check your connection.")
    blobs = [t for t in tree.get("tree", []) if t["type"] == "blob" and not JUNK & set(Path(t["path"]).parts)
             and t.get("size", 0) < 1_000_000]
    if tree.get("truncated") or len(blobs) > FETCH_FILES or sum(t.get("size", 0) for t in blobs) > MAX_BYTES:
        return None, (f"That project is too big to fetch here (over {FETCH_FILES} files). Download its zip from GitHub "
                      "(Code, then Download ZIP) and drop it here instead.")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for start in range(0, len(blobs), 24):  # a few at a time: quick, and kind to GitHub
            batch = blobs[start:start + 24]
            datas = await asyncio.gather(*(_get(f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{t['path']}") for t in batch),
                                         return_exceptions=True)
            for t, data in zip(batch, datas):
                if isinstance(data, bytes):
                    z.writestr(f"{repo}/{t['path']}", data)
    return out.getvalue(), f"{repo}.zip"


def kind(root: Path) -> dict:
    """How the project runs: {"kind": "asgi"/"wsgi", "module", "var"}, {"kind": "static", "folder"}, or {"kind": "tests"}."""
    for path in pieces.python_files(root):
        source = path.read_text(errors="replace")
        found = re.search(r"^(\w+)\s*=\s*(FastAPI|Starlette|Flask)\(", source, re.M)
        if found:
            module = ".".join(path.relative_to(root).with_suffix("").parts)
            return {"kind": "wsgi" if found[2] == "Flask" else "asgi", "module": module, "var": found[1]}
    pages = sorted(root.rglob("index.html"), key=lambda p: len(p.parts))
    pages = [p for p in pages if not JUNK & set(p.relative_to(root).parts)]
    if pages:
        return {"kind": "static", "folder": str(pages[0].parent.relative_to(root))}
    return {"kind": "tests"}


def requirements(root: Path) -> list[str]:
    path = root / "requirements.txt"
    if not path.exists():
        return []
    return [line.split("#")[0].strip() for line in path.read_text(errors="replace").splitlines()
            if line.split("#")[0].strip() and not line.startswith(("-", "git+"))]


def needs(root: Path) -> list[str]:
    """Packages to install before running or testing: what the code imports (mapped to package names, e.g.
    PIL -> pillow) plus what requirements.txt lists, without version pins (a pin browser Python can't match would
    stop the install), and never the ones that can't run in a browser anyway."""
    from tutor import compat
    built_in = compat.BUILTIN["imports"]
    report_ = compat.load(root.name) or {}
    impossible = {l["name"] for l in report_.get("libraries", []) if l["status"] == "can't run in a browser"}
    imported = set().union(*compat._imports(root).values()) if compat._imports(root) else set()
    names = {built_in.get(m) or compat.KNOWN.get(m, m) for m in imported - impossible}
    names |= {re.split(r"[<>=!~\[; ]", r)[0].strip() for r in requirements(root)} - impossible
    return sorted(n for n in names if n)


def explain_start_error(text: str) -> str:
    """Plain words for why an uploaded app couldn't start, from its error (the technical text stays below it)."""
    rules = [
        (r"no such table: (\w+)", "The app reads a database table ({0}) when it starts, but the project doesn't include that "
                                   "database. It's usually created by another script or on the original machine, "
                                   "so the app has no data to show here."),
        (r"unable to open database file", "The app opens a database file that isn't in the project."),
        (r"No module named '([\w.]+)'", "The app needs the library {0}, which couldn't be installed here."),
        (r"No such file or directory: '([^']+)'", "The app needs a file that isn't in the project: {0}."),
        (r"Adafruit|RPi\.GPIO|smbus|spidev|picamera", "The app is written for special hardware (like a Raspberry Pi with "
                                                    "sensors), which a browser or a normal computer doesn't have."),
    ]
    for pattern, words in rules:
        found = re.search(pattern, text)
        if found:
            return words.format(*found.groups())
    return "The app raised an error while starting."


def report(name: str) -> dict:
    """The safety check's result for an uploaded project (tutor/safety.py writes it)."""
    path = progress.DATA / "work" / name / "safety.json"
    return json.loads(path.read_text()) if path.exists() else {"blocked": True, "reasons": ["Not checked yet."]}


def _count(root: Path) -> tuple[int, int]:
    """(pieces, files) in a project's own code, in every language Carve-Out reads."""
    import ast
    files = pieces.python_files(root)
    functions = 0
    for f in files:
        try:
            functions += sum(isinstance(n, ast.FunctionDef) for n in ast.parse(f.read_text(errors="replace")).body)
        except SyntaxError:
            pass
    others = [f for f in pieces.other_files(root) if langs.find(f.read_text(errors="replace"), langs.lang(f))]
    functions += sum(len(langs.find(f.read_text(errors="replace"), langs.lang(f))) for f in others)
    return functions, len(files) + len(others)


def languages(root: Path) -> list[str]:
    """The languages of a project's own code, most files first: ["Java", "SQL"]."""
    count: dict[str, int] = {}
    for f in pieces.source_files(root):
        count[langs.NAMES[langs.lang(f)]] = count.get(langs.NAMES[langs.lang(f)], 0) + 1
    return sorted(count, key=lambda k: -count[k])


def listing() -> list[dict]:
    """The uploaded projects, for the catalog: kind, size, the safety check, and whether they run in the browser."""
    from tutor import compat
    out = []
    for p in sorted(UPLOADS.iterdir()) if UPLOADS.exists() else []:
        if not p.is_dir():
            continue
        functions, files = _count(p)
        fit = compat.load(p.name)
        out.append({"name": p.name, "kind": kind(p)["kind"], "functions": functions, "files": files, "languages": languages(p),
                    "fit": fit["verdict"] if fit else None,
                    **{k: v for k, v in report(p.name).items() if k in ("blocked", "reasons", "warnings")}})
    return out


def active() -> str:
    return json.loads(ACTIVE.read_text())["name"] if ACTIVE.exists() else "store"


def activate(name: str) -> str | None:
    """Makes a project the one being learned. Returns why not, if it can't be (missing, or blocked by the check)."""
    if name != "store":
        if not (UPLOADS / name).is_dir():
            return "That project isn't there anymore."
        if report(name)["blocked"]:
            return "That project didn't pass the safety check, so it can't be opened."
    pieces.use(pieces.BUILTIN if name == "store" else UPLOADS / name)
    progress.DATA.mkdir(parents=True, exist_ok=True)
    ACTIVE.write_text(json.dumps({"name": name}))
    return None


def download() -> tuple[str, bytes]:
    """The active project as a zip, with every function the learner passed swapped in."""
    prog = progress.load()
    mine = {PIECES[p]["file"]: assemble(p, progress.passed_snippets(prog, p)) for p in progress.swapped(prog)}
    root = pieces.STORE
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and not JUNK & set(rel.parts) and path.suffix != ".db":
                z.writestr(f"{root.name}/{rel}", mine.get(str(rel), None) or path.read_bytes())
    name = "polyvault" if root == pieces.BUILTIN else root.name
    return f"{name}-with-my-code.zip", out.getvalue()
