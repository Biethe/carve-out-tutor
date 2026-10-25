"""Uploaded projects: unpacked from a zip into data/uploads/<name>/, checked for harmful code before anything runs,
and downloaded back as a zip with the learner's passed functions inside. Polyvault (store/) is the built-in one."""
import io
import json
import re
import zipfile
from pathlib import Path

from tutor import pieces, progress
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
    if not any(n.endswith(".py") for n in names) and not any(Path(n).name == "index.html" for n in names):
        return None, "There's no Python code and no web page (index.html) in that zip."
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


def report(name: str) -> dict:
    """The safety check's result for an uploaded project (tutor/safety.py writes it)."""
    path = progress.DATA / "work" / name / "safety.json"
    return json.loads(path.read_text()) if path.exists() else {"blocked": True, "reasons": ["Not checked yet."]}


def listing() -> list[dict]:
    return [{"name": p.name, "kind": kind(p)["kind"], **{k: v for k, v in report(p.name).items() if k in ("blocked", "reasons", "warnings")}}
            for p in sorted(UPLOADS.iterdir()) if p.is_dir()] if UPLOADS.exists() else []


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
