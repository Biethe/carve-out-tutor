"""The project at a glance: its file tree, and a diagram of how its files depend on each other.
Both are read live from store/, so they never go stale."""
import ast
from pathlib import Path

from tutor.pieces import STORE

SKIP = {"__pycache__"}


def tree(path: Path = STORE) -> list[dict]:
    """[{name, path, dir, about, children}] with folders first. `about` is a .py file's docstring, first line."""
    items = []
    for p in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name)):
        if p.name in SKIP or p.name.startswith("."):
            continue
        item = {"name": p.name, "path": str(p.relative_to(STORE.parent)), "dir": p.is_dir(), "about": ""}
        if p.is_dir():
            item["children"] = tree(p)
        elif p.suffix == ".py":
            item["about"] = (ast.get_docstring(ast.parse(p.read_text())) or "").split("\n")[0]
        items.append(item)
    return items


def _uses(source: str, modules: set[str]) -> dict[str, set[str]]:
    """Which project modules a file uses, and the names it uses from each."""
    used: dict[str, set[str]] = {}
    aliases = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                if f"{node.module}.{a.name}" in modules:  # from pieces import auth
                    aliases[a.asname or a.name] = f"{node.module}.{a.name}"
                    used.setdefault(f"{node.module}.{a.name}", set())
                elif node.module in modules:  # from pieces.auth import hash_password
                    used.setdefault(node.module, set()).add(a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name in modules:
                    aliases[a.asname or a.name] = a.name
                    used.setdefault(a.name, set())
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases:
            used[aliases[node.value.id]].add(node.attr)
    return used


def diagram(current_file: str | None = None) -> str:
    """A Mermaid flowchart: browser -> routes -> pieces and database, labelled with the functions each file calls."""
    files = sorted(STORE.rglob("*.py"))
    modules = {".".join(f.relative_to(STORE).with_suffix("").parts): f for f in files}
    node = {m: f"m{i}" for i, m in enumerate(modules)}
    lines = ["flowchart TB", '  browser(["Browser"])']
    for m, f in modules.items():
        lines.append(f'  {node[m]}["{f.relative_to(STORE)}"]')
    for m, f in modules.items():
        source = f.read_text()
        if "FastAPI(" in source:
            lines.append(f'  browser -->|"HTTP requests, session cookie"| {node[m]}')
        if "Jinja2Templates" in source:
            lines += ['  templates[/"templates/*.html"/]', f'  {node[m]} -->|"renders pages"| templates']
        if "sqlite3" in source:
            lines += ['  sqlite[("store.db")]', f'  {node[m]} <-->|"SQL"| sqlite']
        for dep, names in _uses(source, set(modules)).items():
            label = ", ".join(sorted(names)[:3]) + (", ..." if len(names) > 3 else "")
            lines.append(f'  {node[m]} -->|"{label or "imports"}"| {node[dep]}')
    if current_file:
        lines += ["  classDef you stroke-width:4px,stroke-dasharray:6 4"]
        lines += [f"  class {node[m]} you" for m, f in modules.items() if str(f.relative_to(STORE.parent)) == current_file]
    return "\n".join(lines)


if __name__ == "__main__":
    out = diagram("store/pieces/cart.py")
    assert 'm0["app.py"]' in out and "check_login" in out and "class" in out and "store.db" in out, out
    assert any(i["name"] == "pieces" and i["dir"] for i in tree())
    print(out)
