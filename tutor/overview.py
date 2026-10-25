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
        return re.sub(r"\b\w+\.", "", ast.unparse(r)).replace(" | ", " or ") if r else "result"  # sqlite3.Row -> Row

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


# Limits that keep every diagram readable, whatever project it's drawn from.
EDGE_MAX = 36   # characters on an arrow: short data labels only, never signatures
BOX_MAX = 7     # functions listed in a file's box
LINE_MAX = 50   # characters per line in a box


def _fit(names: list[str], limit: int = EDGE_MAX) -> str:
    """Names joined while they fit on one short line, then "+N more"."""
    shown: list[str] = []
    for name in names:
        if shown and len(", ".join(shown + [name])) > limit - 8:
            break
        shown.append(name[:limit - 9] + "…" if len(name) > limit - 8 else name)
    rest = len(names) - len(shown)
    return ", ".join(shown) + (f" +{rest} more" if rest else "")


def system(current_file: str | None = None, project: Project | None = None, current_fn: str | None = None) -> str:
    """UML-style component diagram. Each file's box lists the functions other files call, with what goes in and
    comes out. Arrows carry short labels: the data that travels (form fields, session keys, SQL) or what's called."""
    p = project or Project()
    forms, keys, calls, used = set(), set(), {}, {}
    for _, _, _, fn in p.routes():
        forms.update(_form_fields(fn))
    for (m, _), fn in p.funcs.items():
        r, w = _session(fn)
        keys |= r | w
        for cm, cn, _ in p.calls(m, fn):
            if cm != m:
                calls.setdefault((m, cm), set()).add(cn)
                used.setdefault(cm, set()).add(cn)
    mine = next((m for m in p.files if str(p.files[m].relative_to(STORE.parent)) == current_file), None)
    lines = ["flowchart TB", '  browser(["Browser"])']
    for m in p.files:
        star = lambda n: "★ " if m == mine and n == current_fn else ""  # noqa: E731
        rows = [f"{star(n)}{n}({', '.join(a.arg for a in p.funcs[(m, n)].args.args)}) → {p.returns(m, n)}" for n in sorted(used.get(m, ()))]
        rows = [r if len(r) <= LINE_MAX else r[:LINE_MAX - 1] + "…" for r in rows]
        if len(rows) > BOX_MAX:
            rows = rows[:BOX_MAX - 1] + [f"+{len(rows) - BOX_MAX + 1} more"]
        routes = sum(1 for r in p.routes() if r[2] == m)
        if routes:
            rows.insert(0, f"{routes} routes: the pages and forms")
        lines.append(f'  {_id(m)}["<b>{p.path(m)}</b>{"".join("<br>" + r for r in rows)}"]')
    app = next((m for m, s in p.sources.items() if "FastAPI(" in s or "Flask(" in s), None)
    if app:
        lines.append(f'  browser <-->|"forms in · pages out"| {_id(app)}')
        if keys:
            lines += ['  session[["session cookie"]]', f'  {_id(app)} <-->|"{_fit(sorted(keys))}"| session']
    for m, s in p.sources.items():
        tables = re.findall(r"CREATE TABLE(?: IF NOT EXISTS)? (\w+)", s)
        if tables:
            lines += [f'  sqlite[("<b>store.db</b><br>{" · ".join(tables)}")]', f'  {_id(m)} <-->|"SQL"| sqlite']
    for (a, b), names in calls.items():
        if mine in (a, b):  # arrows touching your file: thick, and labelled with what's called
            lines.append(f'  {_id(a)} ==>|"{_fit(sorted(names))}"| {_id(b)}')
        else:  # the rest: no label, the box at the end already lists what's called
            lines.append(f"  {_id(a)} --> {_id(b)}")
    lines += _you(p, current_file)
    return "\n".join(lines)


def _you(p: Project, current_file: str | None) -> list[str]:
    mine = [m for m in p.files if current_file and str(p.files[m].relative_to(STORE.parent)) == current_file]
    return ["  classDef you stroke-width:4px,stroke-dasharray:6 4"] + [f"  class {_id(m)} you" for m in mine] if mine else []


def _safe(text: str, limit: int = 60) -> str:
    text = re.sub(r"[;#]", " ", text)  # both mean something to Mermaid
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _session_ops(node: ast.AST) -> list[str]:
    """What one statement does with the session cookie, in plain words, in the order it happens."""
    ops = []
    for n in sorted(ast.walk(node), key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0))):
        target = isinstance(n, ast.Subscript) and n.value or isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.value
        if not target or not ast.unparse(target).endswith("session"):
            continue
        key = n.slice if isinstance(n, ast.Subscript) else (n.args[0] if n.args else None)
        key = key.value if isinstance(key, ast.Constant) else "everything"
        if isinstance(n, ast.Subscript):
            ops.append(("saves " if isinstance(n.ctx, ast.Store) else "reads ") + key)
        elif n.func.attr in ("get", "pop", "clear"):
            ops.append({"get": "reads ", "pop": "reads and removes ", "clear": "clears "}[n.func.attr] + key)
    return ops


def _reply(p: Project, app: str, node: ast.AST) -> str | None:
    """What a route's `return` or `raise` sends back to the browser, in plain words."""
    value = node.value if isinstance(node, ast.Return) else node.exc
    if not isinstance(value, ast.Call):
        return None
    name = getattr(value.func, "id", None) or getattr(value.func, "attr", "")
    source = ast.unparse(value) + (ast.unparse(p.funcs[(app, name)]) if (app, name) in p.funcs else "")
    texts = [c.value for c in ast.walk(value) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    if isinstance(node, ast.Raise):
        code = next((c.value for c in ast.walk(value) if isinstance(c, ast.Constant) and isinstance(c.value, int)), "")
        return f"stops with error {code}".strip()
    if "RedirectResponse" in source:
        return "sends the browser to " + next((t for t in texts if t.startswith("/")), "another page")
    if "FileResponse" in source:
        return "sends back the file"
    if "TemplateResponse" in source:
        return "sends back the page " + next((t for t in texts if t.endswith(".html")), "")
    return "sends back the answer"


def flow(verb: str, path: str, current: tuple[str, str] | None = None, project: Project | None = None) -> tuple[str, set]:
    """Sequence diagram of one request, read top to bottom: numbered steps from the browser's request to what comes
    back, with if/else branches and loops (and when each loop ends). Also returns the (file, function)s it reaches."""
    p = project or Project()
    _, _, app, fn = next(r for r in p.routes() if r[:2] == (verb, path))
    parts = {"browser": "Browser", app: p.path(app)}
    reached = set()
    # A function no other file calls is a private helper (render, connect): show what it does, not the hop.
    public = {(cm, cn) for (m, _), f in p.funcs.items() for cm, cn, _ in p.calls(m, f) if cm != m}

    def calls(m: str, node: ast.AST, caller: str, depth: int) -> list[str]:
        out = []
        for cm, cn, _ in p.calls(m, node):
            if cm == m and (cm, cn) not in public:
                out += body(cm, p.funcs[(cm, cn)].body, caller, depth, top=False)
                continue
            parts[cm] = p.path(cm)
            reached.add((cm, cn))
            params = ", ".join(a.arg for a in p.funcs[(cm, cn)].args.args)
            mine = " ★ your code" if current == (cm, cn) else ""
            out.append(f"{_id(caller)}->>{_id(cm)}: calls {cn}({params}){mine}")
            if depth < 3:
                out += body(cm, p.funcs[(cm, cn)].body, cm, depth + 1, top=False)
            out.append(f"{_id(cm)}-->>{_id(caller)}: gives back {p.returns(cm, cn)}")
        return out

    def body(m: str, stmts: list[ast.stmt], caller: str, depth: int, top: bool) -> list[str]:
        """Steps for a list of statements. `top` is the route itself, where returns answer the browser."""
        out = []
        for i, s in enumerate(stmts):
            if isinstance(s, (ast.For, ast.While)):
                out += calls(m, s.iter if isinstance(s, ast.For) else s.test, caller, depth)  # runs before the loop starts
                inner = body(m, s.body, caller, depth, top)
                if inner:
                    end = (f"for each {ast.unparse(s.target)} in {ast.unparse(s.iter)}, until the last one"
                           if isinstance(s, ast.For) else f"while {ast.unparse(s.test)}, until that's false")
                    out += [f"loop {_safe(end)}", *inner, "end"]
            elif isinstance(s, ast.If):
                out += calls(m, s.test, caller, depth)  # the condition runs first, then one branch
                # A branch that ends by answering makes the rest of the function the "otherwise" branch.
                early = top and not s.orelse and isinstance(s.body[-1], (ast.Return, ast.Raise))
                yes = body(m, s.body, caller, depth, top)
                no = body(m, stmts[i + 1:] if early else s.orelse, caller, depth, top)
                called = s.test.func if isinstance(s.test, ast.Call) else None
                test = (f"{getattr(called, 'attr', None) or getattr(called, 'id', '')} gives back True"
                        if called is not None else ast.unparse(s.test))
                if early:
                    out += [f"alt if {_safe(test)}", *yes, "else otherwise", *no, "end"] if no else [f"opt if {_safe(test)}", *yes, "end"]
                    break
                if yes and no:
                    out += [f"alt if {_safe(test)}", *yes, "else otherwise", *no, "end"]
                elif yes or no:  # only one side does anything: show just that side
                    out += [f"opt if {_safe(test if yes else f'not ({test})')}", *(yes or no), "end"]
            elif isinstance(s, (ast.With, ast.Try)):
                for item in getattr(s, "items", []):
                    out += calls(m, item.context_expr, caller, depth)
                for part in ("body", "orelse", "finalbody"):
                    out += body(m, getattr(s, part, []), caller, depth, top)
            else:
                out += calls(m, s, caller, depth)
                if m == app:
                    out += [f"{_id(app)}->>session: {op}" for op in _session_ops(s)]
                    if any(op for op in _session_ops(s)):
                        parts["session"] = "session cookie"
                if m != app and "execute" in ast.unparse(s):
                    parts["sqlite"] = "store.db"
                    out += [f"{_id(m)}->>sqlite: runs SQL", f"sqlite-->>{_id(m)}: gives back rows"]
                if top and isinstance(s, (ast.Return, ast.Raise)) and (reply := _reply(p, app, s)):
                    out.append(f"{_id(app)}-->>browser: {reply}")
        return out

    fields = _form_fields(fn) + re.findall(r"{(\w+)}", path)
    steps = [f"browser->>{_id(app)}: {verb} {path}" + (f" with {', '.join(fields)}" if fields else "")]
    steps += body(app, fn.body, app, 0, top=True)
    head = ["sequenceDiagram", "  autonumber"] + [f"  participant {_id(m)} as {label}" for m, label in parts.items()]
    return "\n".join(head + ["  " + _safe(s, 90) for s in steps]), reached


def diagrams(current_file: str | None = None, current_fn: str | None = None) -> dict:
    """The system map, plus only the requests that matter to the learner now: those that reach their function,
    else those that reach their file. With nothing to work on, every request."""
    p = Project()
    module = current_file and ".".join(Path(current_file).relative_to("store").with_suffix("").parts)
    current = (module, current_fn) if module else None
    flows = [(f"{v} {path}", *flow(v, path, current, p)) for v, path, _, _ in p.routes()]
    relevant = ([f for f in flows if current in f[2]] or [f for f in flows if any(m == module for m, _ in f[2])] or flows)
    return {
        "system": system(current_file, p, current_fn),
        "flows": [{"name": name, "diagram": text} for name, text, _ in relevant],
    }


if __name__ == "__main__":
    d = diagrams("store/pieces/auth.py", "check_login")
    assert "check_login(username, password, users) → bool" in d["system"] and "users · assets" in d["system"]
    labels = re.findall(r'\|"([^"]*)"\|', d["system"] + "".join(f["diagram"] for f in d["flows"]))
    assert all(len(label) <= EDGE_MAX and "<br>" not in label for label in labels), labels  # arrows stay short
    assert "★ check_login" in d["system"] and "==>" in d["system"]  # your function and its arrows stand out
    assert {f["name"] for f in d["flows"]} == {"POST /login"}, [f["name"] for f in d["flows"]]  # only what reaches it
    login = d["flows"][0]["diagram"]
    assert login.index("get_users") < login.index("check_login("), login  # arguments run before the call
    assert "autonumber" in login and "★ your code" in login and "alt if check_login gives back True" in login, login
    assert login.index("saves username") < login.index("else otherwise") < login.index("login.html"), login
    assert "sends the browser to /" in login and "sends back the page login.html" in login, login
    cart = diagrams("store/pieces/cart.py", "cart_total")
    assert [f["name"] for f in cart["flows"]] == ["GET /cart"], cart["flows"]
    assert all(set(i) == {"name", "path", "dir", "children"} or set(i) == {"name", "path", "dir"} for i in tree())
    print(d["system"]), print(login)
