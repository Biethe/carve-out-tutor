"""The project at a glance: its file names, and UML-style diagrams of how data flows through it.
Everything is read live from store/ with ast, so it never goes stale."""
import ast
import re
from pathlib import Path

from tutor.pieces import STORE

SKIP = {"__pycache__"}
VERBS = {"get", "post", "put", "delete", "patch"}


def tree(path: Path = STORE) -> list[dict]:
    """[{name, path, dir, children}], folders first. Names only: the learner never sees file contents here."""
    items = []
    for p in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name)):
        if p.name in SKIP or p.name.startswith("."):
            continue
        item = {"name": p.name, "path": str(p.relative_to(STORE.parent)), "dir": p.is_dir()}
        if p.is_dir():
            item["children"] = tree(p)
        items.append(item)
    return items


class Project:
    """Every top-level function of every .py file, and what each name in a file refers to."""

    def __init__(self, root: Path = STORE):
        self.files = {".".join(f.relative_to(root).with_suffix("").parts): f for f in sorted(root.rglob("*.py"))
                      if not SKIP & set(f.parts)}
        self.sources = {m: f.read_text() for m, f in self.files.items()}
        self.trees = {m: ast.parse(s) for m, s in self.sources.items()}
        self.funcs = {(m, n.name): n for m, t in self.trees.items() for n in t.body if isinstance(n, ast.FunctionDef)}
        self.names = {m: self._names(m) for m in self.files}

    def _names(self, module: str) -> dict[str, tuple[str, str | None]]:
        """alias -> (module, function or None for a whole module)."""
        names = {name: (module, name) for (m, name) in self.funcs if m == module}
        for node in self.trees[module].body:
            if isinstance(node, ast.Import):
                names.update({a.asname or a.name: (a.name, None) for a in node.names if a.name in self.files})
            elif isinstance(node, ast.ImportFrom) and node.module:
                for a in node.names:
                    if f"{node.module}.{a.name}" in self.files:  # from pieces import auth
                        names[a.asname or a.name] = (f"{node.module}.{a.name}", None)
                    elif node.module in self.files:  # from pieces.auth import hash_password
                        names[a.asname or a.name] = (node.module, a.name)
        return names

    def path(self, module: str) -> str:
        return str(self.files[module].relative_to(STORE))

    def calls(self, module: str, fn: ast.FunctionDef) -> list[tuple[str, str, list[str]]]:
        """Project functions this function calls, in the order they run: [(module, name, argument texts)]."""
        found = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            target = None
            if isinstance(f, ast.Name):
                target = self.names[module].get(f.id)
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                mod = self.names[module].get(f.value.id)
                target = mod and mod[1] is None and (mod[0], f.attr)
            if target and target[1] and target in self.funcs:
                found.append(((node.end_lineno, node.end_col_offset), target, [_short(a) for a in node.args]))
        return [(m, n, args) for _, (m, n), args in sorted(found)]  # inner calls end first, so they run first

    def returns(self, module: str, name: str) -> str:
        r = self.funcs[(module, name)].returns
        return ast.unparse(r).replace(" | ", " or ") if r else "result"

    def routes(self) -> list[tuple[str, str, str, ast.FunctionDef]]:
        """[(VERB, path, module, function)] for every @app.get/post/... route."""
        out = []
        for (m, _), fn in self.funcs.items():
            for d in fn.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in VERBS
                        and d.args and isinstance(d.args[0], ast.Constant)):
                    out.append((d.func.attr.upper(), d.args[0].value, m, fn))
        return out


def _short(node: ast.AST) -> str:
    text = re.sub(r"[;#]", " ", ast.unparse(node))  # both mean something to Mermaid
    return text if len(text) <= 24 else text[:21] + "..."


def _form_fields(fn: ast.FunctionDef) -> list[str]:
    defaults = fn.args.defaults
    args = fn.args.args[len(fn.args.args) - len(defaults):]
    return [a.arg for a, d in zip(args, defaults) if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "Form"]


def _session(fn: ast.FunctionDef) -> tuple[set[str], set[str]]:
    """Keys this function reads from and writes to request.session."""
    reads, writes = set(), set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Subscript) and ast.unparse(node.value).endswith("session") and isinstance(node.slice, ast.Constant):
            (writes if isinstance(node.ctx, ast.Store) else reads).add(node.slice.value)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and ast.unparse(node.func.value).endswith("session") and node.args and isinstance(node.args[0], ast.Constant)):
            (writes if node.func.attr == "pop" else reads).add(node.args[0].value)
    return reads, writes


def _id(path: str) -> str:
    return re.sub(r"\W", "_", path)


def system(current_file: str | None = None, project: Project | None = None) -> str:
    """Component diagram: who talks to whom, and what data travels on each arrow."""
    p = project or Project()
    lines = ["flowchart LR", '  browser(["Browser"])']
    for m in p.files:
        lines.append(f'  {_id(m)}["{p.path(m)}"]')
    forms, keys, edges = set(), set(), {}
    for verb, path, m, fn in p.routes():
        forms.update(_form_fields(fn))
    for (m, name), fn in p.funcs.items():
        r, w = _session(fn)
        keys |= r | w
        for cm, cn, _ in p.calls(m, fn):
            if cm != m:
                params = [a.arg for a in p.funcs[(cm, cn)].args.args]
                edges.setdefault((m, cm), set()).add(f"{cn}({', '.join(params)}) → {p.returns(cm, cn)}")
    app = next((m for m, s in p.sources.items() if "FastAPI(" in s or "Flask(" in s), None)
    if app:
        label = "forms: " + ", ".join(sorted(forms)) if forms else "requests"
        lines += [f'  browser -->|"{label}"| {_id(app)}', f'  {_id(app)} -->|"HTML pages"| browser']
        if keys:
            lines += ['  session[["session cookie"]]', f'  {_id(app)} <-->|"{", ".join(sorted(keys))}"| session']
    for m, s in p.sources.items():
        tables = re.findall(r"CREATE TABLE(?: IF NOT EXISTS)? (\w+)", s)
        if tables:
            lines += ['  sqlite[("store.db")]', f'  {_id(m)} <-->|"tables: {", ".join(tables)}"| sqlite']
    for (a, b), labels in edges.items():
        shown = sorted(labels)[:4] + (["..."] if len(labels) > 4 else [])
        lines.append(f'  {_id(a)} -->|"{"<br>".join(shown)}"| {_id(b)}')
    lines += _you(p, current_file)
    return "\n".join(lines)


def _you(p: Project, current_file: str | None) -> list[str]:
    mine = [m for m in p.files if current_file and str(p.files[m].relative_to(STORE.parent)) == current_file]
    return ["  classDef you stroke-width:4px,stroke-dasharray:6 4"] + [f"  class {_id(m)} you" for m in mine] if mine else []


def flow(verb: str, path: str, current: tuple[str, str] | None = None, project: Project | None = None) -> str:
    """Sequence diagram of one request: every project function it reaches, in order, with what goes in and comes out."""
    p = project or Project()
    verb_path = next(r for r in p.routes() if r[:2] == (verb, path))
    _, _, app, fn = verb_path
    parts = {"browser": "Browser", app: p.path(app)}
    steps = []
    fields = _form_fields(fn) + re.findall(r"{(\w+)}", path)
    steps.append(f"browser->>{_id(app)}: {verb} {path}" + (f" ({', '.join(fields)})" if fields else ""))
    reads, writes = set(), set()
    responses = set()
    # A function no other file calls is a private helper (render, connect): show what it does, not the hop.
    public = {(cm, cn) for (m, _), f in p.funcs.items() for cm, cn, _ in p.calls(m, f) if cm != m}

    def walk(m: str, f: ast.FunctionDef, caller: str, depth: int):
        r, w = _session(f)
        reads.update(r), writes.update(w)
        source = ast.unparse(f)
        responses.update(k for k in ("TemplateResponse", "RedirectResponse", "FileResponse") if k in source)
        for cm, cn, args in p.calls(m, f):
            if cm == m and (cm, cn) not in public:
                walk(cm, p.funcs[(cm, cn)], caller, depth)
                continue
            parts[cm] = p.path(cm)
            steps.append(f"{_id(caller)}->>{_id(cm)}: {cn}({', '.join(args)})")
            if current == (cm, cn):
                steps.append(f"Note over {_id(cm)}: you write {cn}")
            if depth < 3:
                walk(cm, p.funcs[(cm, cn)], cm, depth + 1)
            steps.append(f"{_id(cm)}-->>{_id(caller)}: {p.returns(cm, cn)}")
        if "execute" in source and m != app:
            parts["sqlite"] = "store.db"
            steps.extend([f"{_id(m)}->>sqlite: SQL", f"sqlite-->>{_id(m)}: rows"])

    walk(app, fn, app, 0)
    if reads or writes:
        note = " · ".join(x for x in (reads and "reads " + ", ".join(sorted(reads)), writes and "writes " + ", ".join(sorted(writes))) if x)
        steps.append(f"Note over {_id(app)}: session cookie: {note}")
    reply = {"RedirectResponse": "redirect", "FileResponse": "file", "TemplateResponse": "HTML page"}
    steps.append(f"{_id(app)}-->>browser: " + " or ".join(reply[k] for k in sorted(responses)) if responses else f"{_id(app)}-->>browser: response")
    head = ["sequenceDiagram"] + [f"  participant {_id(m)} as {label}" for m, label in parts.items()]
    return "\n".join(head + ["  " + s for s in steps])


def diagrams(current_file: str | None = None, current_fn: str | None = None) -> dict:
    p = Project()
    module = current_file and ".".join(Path(current_file).relative_to("store").with_suffix("").parts)
    current = (module, current_fn) if module else None
    return {
        "system": system(current_file, p),
        "flows": [{"name": f"{v} {path}", "diagram": flow(v, path, current, p)} for v, path, _, _ in p.routes()],
    }


if __name__ == "__main__":
    d = diagrams("store/pieces/auth.py", "check_login")
    assert "check_login(username, password, users) → bool" in d["system"] and "tables: users" in d["system"]
    login = next(f["diagram"] for f in d["flows"] if f["name"] == "POST /login")
    assert login.index("get_users") < login.index("check_login("), login  # arguments run before the call
    assert "you write check_login" in login and "writes" in login and "username" in login, login
    assert all(set(i) == {"name", "path", "dir", "children"} or set(i) == {"name", "path", "dir"} for i in tree())
    print(d["system"]), print(login)
