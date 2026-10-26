"""Can an uploaded project run in the browser? Checked right after upload, next to the safety check.
Each library it needs is built into browser Python (Pyodide), installable (a pure-Python wheel on PyPI), or impossible
there (compiled code nobody has ported, like psycopg2 or torch). A file that needs an impossible library can't be
imported, so its functions can't be tested in the browser: they're left out of the plan, with the reason. Some things
need a real machine whatever the library: a database server, threads, other programs, outside network calls.
In the local tutor (your own Python) none of this applies: pip installs everything."""
import ast
import asyncio
import json
import re
import sys
import urllib.request
from pathlib import Path

from tutor import langs, pieces, progress

BUILTIN = json.loads((Path(__file__).parent / "pyodide_packages.json").read_text())
STDLIB = set(sys.stdlib_module_names)
# Import names that differ from their package names, for libraries not built into browser Python.
KNOWN = {"psycopg2": "psycopg2", "MySQLdb": "mysqlclient", "torch": "torch", "tensorflow": "tensorflow", "dotenv": "python-dotenv"}
MACHINE = [  # (what it needs, pattern): fine on a computer, not in a browser tab
    ("a database server", r"\b(psycopg2?|pymysql|MySQLdb|redis|pymongo|motor|asyncpg)\b"),
    ("background threads or processes", r"\bthreading\.Thread\b|\bmultiprocessing\b|\bProcessPoolExecutor\b|\bThreadPoolExecutor\b"),
    ("running other programs", r"\bsubprocess\b|\bos\.system\("),
    ("its own network connections", r"\bsocket\.socket\(|\bwebsockets?\b"),
]


def in_browser() -> bool:
    return sys.platform == "emscripten"


async def _pure_python_on_pypi(package: str) -> bool | None:
    """True if PyPI has a pure-Python wheel (micropip can install it), False if not, None if PyPI can't be reached."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        if in_browser():
            from pyodide.http import pyfetch
            reply = await pyfetch(url)
            if reply.status == 404:
                return False
            data = await reply.json()
        else:
            def get():
                with urllib.request.urlopen(url, timeout=15) as r:
                    return json.load(r)
            data = await asyncio.to_thread(get)
    except Exception as err:
        return False if "404" in str(err) else None
    return any(f["filename"].endswith("-none-any.whl") for f in data.get("urls", []))


def _imports(root: Path) -> dict[str, set[str]]:
    """Top-level outside modules each project file imports: {"app.py": {"flask", "psycopg2"}}."""
    local = {p.stem for p in root.iterdir()} | {p.name for p in root.iterdir() if p.is_dir()}
    found = {}
    for path in pieces.python_files(root):
        try:
            tree = ast.parse(path.read_text(errors="replace"))
        except SyntaxError:
            continue
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
        found[str(path.relative_to(root))] = {n for n in names if n not in STDLIB and n not in local}
    return found


async def check(name: str, root: Path) -> dict:
    """{verdict, libraries: [{name, status}], blocked: {file: [libraries]}, machine: [needs]}; saved for the project.
    verdict: "full" (everything runs in the browser), "partial", or "none"."""
    from tutor import projects
    imports = _imports(root)
    wanted = {re.split(r"[<>=!~\[; ]", r)[0].strip().lower() for r in projects.requirements(root)} - {""}
    statuses = {}
    for module in sorted(set().union(*imports.values()) if imports else set()):
        if module in BUILTIN["imports"]:
            statuses[module] = "built in"
            continue
        package = KNOWN.get(module, module)
        pure = await _pure_python_on_pypi(package)
        statuses[module] = "installable" if pure else "can't run in a browser" if pure is False else "unknown"
    for package in sorted(wanted - {m.lower() for m in statuses}):  # requirements nobody imports directly (plugins, servers)
        if package not in BUILTIN["packages"] and package.replace("_", "-") not in BUILTIN["packages"]:
            pure = await _pure_python_on_pypi(package)
            if pure is False:
                statuses[package] = "can't run in a browser"
    bad = {m for m, s in statuses.items() if s == "can't run in a browser"}
    # A file that imports a bad library can't load, and neither can a project file that imports that file.
    blocked = {file: sorted(mods & bad) for file, mods in imports.items() if mods & bad}
    module_of = {f.removesuffix(".py").replace("/", "."): f for f in imports}
    changed = True
    while changed:
        changed = False
        for path in pieces.python_files(root):
            file = str(path.relative_to(root))
            if file in blocked:
                continue
            uses = {n.module or "" for n in ast.walk(ast.parse(path.read_text(errors="replace"))) if isinstance(n, ast.ImportFrom)}
            uses |= {a.name for n in ast.walk(ast.parse(path.read_text(errors="replace"))) if isinstance(n, ast.Import) for a in n.names}
            via = [module_of[u] for u in uses if u in module_of and module_of[u] in blocked]
            if via:
                blocked[file] = sorted({lib for f in via for lib in blocked[f]})
                changed = True
    source = "\n".join(p.read_text(errors="replace") for p in pieces.python_files(root))
    machine = [what for what, pattern in MACHINE if re.search(pattern, source)]
    # Compiled languages need their compiler, which the browser version doesn't have (tutor/langs.py).
    others = pieces.other_files(root)
    blocked.update({str(p.relative_to(root)): [langs.TOOLS[langs.lang(p)]] for p in others if langs.lang(p) in langs.TOOLS})
    files = len(imports) + len(others)
    verdict = "none" if files and len(blocked) == files else "partial" if blocked or machine else "full"
    result = {"verdict": verdict, "libraries": [{"name": n, "status": s} for n, s in sorted(statuses.items())],
              "blocked": blocked, "machine": machine}
    path = progress.DATA / "work" / name / "compat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return result


def load(name: str) -> dict | None:
    path = progress.DATA / "work" / name / "compat.json"
    return json.loads(path.read_text()) if path.exists() else None


def blocked_file(file: str) -> list[str] | None:
    """In the browser, the libraries that stop this file of the open project from loading (None if it loads)."""
    if not in_browser() or pieces.STORE == pieces.BUILTIN:
        return None
    if langs.lang(file) in langs.TOOLS:
        return [langs.TOOLS[langs.lang(file)]]
    report = load(pieces.STORE.name) or {}
    return report.get("blocked", {}).get(file)


def why_blocked(file: str) -> str | None:
    if in_browser() and langs.why_not_here(file):
        return langs.why_not_here(file)
    libs = blocked_file(file)
    if not libs:
        return None
    return (f"It needs {', '.join(libs)}, which can't run in a browser. Rebuild it in the local tutor "
            "(on your own computer, with pip install -r requirements.txt).")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "db.py").write_text("import psycopg2\n\ndef connect():\n    return psycopg2.connect('')\n")
        (root / "logic.py").write_text("import numpy\n\ndef mean(xs):\n    return float(numpy.mean(xs))\n")
        (root / "app.py").write_text("from flask import Flask\nimport db\napp = Flask(__name__)\n")
        (root / "requirements.txt").write_text("flask\npsycopg2\nnumpy\n")
        progress.DATA = Path(tmp) / "data"
        r = asyncio.run(check("demo", root))
        print(json.dumps(r, indent=1))
        assert r["verdict"] == "partial", r
        assert set(r["blocked"]) == {"db.py", "app.py"}, r  # app.py imports db.py, which needs psycopg2
        assert {"name": "numpy", "status": "built in"} in r["libraries"]
        assert {"name": "flask", "status": "installable"} in r["libraries"], r["libraries"]
        assert {"name": "psycopg2", "status": "can't run in a browser"} in r["libraries"], r["libraries"]
        assert "a database server" in r["machine"]
    print("compat ok")
