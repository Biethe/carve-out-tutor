"""Projects in languages other than Python: JavaScript, TypeScript, Java, C, C++, Rust, SQL, CSS and HTML.
Finds their pieces (functions; SQL tables, views and queries; CSS rules; HTML sections with an id), swaps the
learner's version in, and checks it the same way for every language: the original code is the reference.
- Code: a short check program (written by the learner's AI) calls the function and prints one "label: value" line per
  check. It runs on the original and on the learner's version, and every line must match.
- SQL, CSS and HTML need no check program: the database, the declarations or the page structure are compared.
JavaScript and TypeScript run in the browser (or Node locally); Java, C, C++ and Rust need their compilers, so they
run in the local tutor. Python projects don't come here: tutor/pieces.py handles them with ast and pytest."""
import asyncio
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

LANGS = {".js": "javascript", ".mjs": "javascript", ".ts": "typescript", ".java": "java", ".c": "c", ".cpp": "cpp",
         ".cc": "cpp", ".cxx": "cpp", ".rs": "rust", ".sql": "sql", ".css": "css", ".html": "html", ".htm": "html"}
NAMES = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript", "java": "Java", "c": "C",
         "cpp": "C++", "rust": "Rust", "sql": "SQL", "css": "CSS", "html": "HTML"}
CODE = {"javascript", "typescript", "java", "c", "cpp", "rust"}  # checked with a check program
TOOLS = {"java": "a Java compiler", "c": "a C compiler", "cpp": "a C++ compiler", "rust": "the Rust compiler"}
TIMEOUT = 15


def lang(file) -> str:
    """The file's language ("" if it isn't one Carve-Out knows)."""
    suffix = Path(str(file)).suffix.lower()
    return "python" if suffix == ".py" else LANGS.get(suffix, "")


def in_browser() -> bool:
    return sys.platform == "emscripten"


def why_not_here(file: str) -> str | None:
    """Every language runs now: compiled ones on Wandbox when there's no compiler here (see run_online). Kept for callers."""
    return None


ONLINE = "Wandbox, a free online compiler"  # where Java, C, C++ and Rust checks run in the browser


# ---- Reading the code: strings and comments blanked out, so brackets can be counted -----------------------------

def _mask(source: str, language: str) -> str:
    """The source with strings and comments turned into spaces (same length, newlines kept)."""
    out = list(source)
    n = len(source)

    def blank(a: int, b: int):
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    line = "--" if language == "sql" else None if language == "css" else "//"
    quotes = {"javascript": "'\"`", "typescript": "'\"`", "sql": "'\"", "css": "'\""}.get(language, '"')
    i = 0
    while i < n:
        c = source[i]
        if language in ("c", "cpp") and c == "#" and not source[source.rfind("\n", 0, i) + 1:i].strip():  # #include, #define
            j = i
            while True:  # a directive ends at the end of its line, unless the line ends with a backslash
                j = source.find("\n", j)
                if j < 0 or source[j - 1] != "\\":
                    break
                j += 1
            j = n if j < 0 else j
        elif line and source.startswith(line, i):
            j = source.find("\n", i)
            j = n if j < 0 else j
        elif source.startswith("/*", i):
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif c in quotes:
            j = i + 1
            while j < n and source[j] != c and not (source[j] == "\n" and c != "`"):
                j += 2 if source[j] == "\\" else 1
            j += 1
        elif c == "'" and language in ("java", "c", "cpp", "rust"):  # a character; in Rust 'a can be a lifetime
            m = re.match(r"'(\\.|\\u\{[0-9a-fA-F]+\}|[^\\'\n])'", source[i:i + 12])
            if not m:
                i += 1
                continue
            j = i + len(m[0])
        else:
            i += 1
            continue
        blank(i, j)
        i = j
    return "".join(out)


CONTROL = {"if", "for", "while", "switch", "catch", "with", "return", "sizeof", "synchronized", "foreach", "else", "do",
           "try", "finally", "new", "await", "typeof", "delete", "function", "using", "lock", "case", "throw"}
_ANNOTATIONS = re.compile(r"@[\w.]+(?:\s*\((?:[^()]|\([^()]*\))*\))?|#!?\[[^\]]*\]|\[\[[^\]]*\]\]|__attribute__\s*\(\(.*?\)\)")
_SUFFIX = {
    "javascript": r"",
    "typescript": r"(?::\s*[^{};=]+)?",
    "java": r"(?:throws\s+[\w.,\s<>]+)?",
    "c": r"(?:const|noexcept|override|final|volatile|&|\s)*(?:->\s*[^{};]+)?|:\s*[\w:]+\s*[({].*",
}
_SUFFIX["cpp"] = _SUFFIX["c"]


def _func_name(header: str, language: str) -> str | None:
    """The function's name if this text right before a { starts a function body, else None."""
    h = _ANNOTATIONS.sub(" ", " ".join(header.split())).strip()
    if not h or h.endswith((";", ",")):
        return None
    if language == "rust":
        m = re.search(r"\bfn\s+([A-Za-z_]\w*)", h)
        return m[1] if m and "|" not in h[m.end():] else None
    if language in ("javascript", "typescript") and h.endswith("=>"):  # const total = (items) => {
        m = re.match(r"(?:export\s+)?(?:(?:const|let|var|static|public|private|protected|readonly|async)\s+)*"
                     r"([A-Za-z_$][\w$]*)\s*(?::[^=]*)?[=:]", h)
        return m[1] if m else None
    # The first (...) right after a name is the parameter list; what follows it must fit the language.
    for m in re.finditer(r"([A-Za-z_$~][\w$~]*(?:::[A-Za-z_~][\w~]*)*)\s*(?:<[^<>()]*(?:<[^<>()]*>[^<>()]*)*>)?\s*\(", h):
        name, before = m[1], h[:m.start()].rstrip()
        depth, end = 0, None
        for k in range(m.end() - 1, len(h)):
            depth += {"(": 1, ")": -1}.get(h[k], 0)
            if depth == 0:
                end = k
                break
        if end is None:
            return None
        suffix = h[end + 1:].strip()
        if name == "function":  # total = function (items) {
            found = re.search(r"([A-Za-z_$][\w$]*)\s*[=:]\s*(?:async\s+)?$", before)
            name, before = (found[1], "") if found else (None, before)
            if not name:
                return None
        if (name.split("::")[-1] in CONTROL or before.endswith((".", "=", "new", "return", "(", ",", "?", ":", "!", "&&", "||"))
                or re.search(r"\b(new|return|throw)$", before)):
            return None
        if not re.fullmatch(_SUFFIX.get(language, ""), suffix):
            return None
        return name
    return None


def _brace_pieces(source: str, language: str) -> list[dict]:
    """Functions not nested in another function: [{name, start, end, open}] (character offsets, end exclusive)."""
    m = _mask(source, language)
    found, stack, last, in_func = [], [], 0, 0
    for i, c in enumerate(m):
        if c == "{":
            header = m[last:i]
            name = None if in_func else _func_name(header, language)
            start = last + len(header) - len(header.lstrip())
            if name:  # the piece starts on its name's line: a return type or annotations on lines above stay outside it
                at = re.search(rf"(?<![\w$]){re.escape(name)}\s*(?:<[^{{}};]*?>)?\s*[(=:]", header)
                if at:
                    start = max(start, m.rfind("\n", 0, last + at.start()) + 1)
                    start += len(m[start:i]) - len(m[start:i].lstrip())
            stack.append((name, start, i))
            in_func += bool(name)
            last = i + 1
        elif c == "}":
            if stack:
                name, start, open_ = stack.pop()
                if name:
                    in_func -= 1
                    found.append({"name": name, "start": start, "open": open_, "end": i + 1})
            last = i + 1
        elif c == ";":
            last = i + 1
    return sorted(found, key=lambda f: f["start"])


def _css_pieces(source: str) -> list[dict]:
    """Rules (and @keyframes), also inside @media; the selector is the name."""
    m = _mask(source, "css")
    found, stack, last = [], [], 0
    for i, c in enumerate(m):
        if c == "{":
            header = " ".join(m[last:i].split())
            container = re.match(r"@(media|supports|layer|container|document)\b", header)
            inside = any(kind == "rule" for kind, _ in stack)
            start = last + len(m[last:i]) - len(m[last:i].lstrip())
            stack.append(("rule" if header and not container and not inside else "other", start))
            last = i + 1
        elif c == "}":
            if stack:
                kind, start = stack.pop()
                if kind == "rule":
                    selector = " ".join(source[start:source.index("{", start)].split())
                    found.append({"name": selector.replace('"', "'"), "start": start, "open": source.index("{", start), "end": i + 1})
            last = i + 1
        elif c == ";" and not stack:
            last = i + 1
    return sorted(found, key=lambda f: f["start"])


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def _html_mask(source: str) -> str:
    out = source
    for pattern in (r"<!--.*?-->", r"(?is)(?<=<script)(?:[^>]*)>.*?(?=</script)", r"(?is)(?<=<style)(?:[^>]*)>.*?(?=</style)"):
        out = re.sub(pattern, lambda x: re.sub(r"[^\n]", " ", x[0]), out, flags=re.S)
    return out


def _html_pieces(source: str) -> list[dict]:
    """Elements with an id that aren't inside another one: <nav id="menu">...</nav>. The id is the name."""
    m = _html_mask(source)
    found, after = [], 0
    for tag in re.finditer(r"<([a-zA-Z][\w-]*)\b[^>]*?\bid\s*=\s*[\"']([^\"']+)[\"'][^>]*>", m):
        if tag.start() < after:
            continue
        name, end = tag[1].lower(), tag.end()
        if name not in VOID and not tag[0].endswith("/>"):
            depth = 1
            for t in re.finditer(rf"<(/?){name}\b[^>]*?(/?)>", m[tag.end():], re.I):
                if t[2]:
                    continue
                depth += -1 if t[1] else 1
                if depth == 0:
                    end = tag.end() + t.end()
                    break
            else:
                continue
        found.append({"name": tag[2], "start": tag.start(), "open": tag.end() - 1, "end": end, "tag": name})
        after = end
    return found


_SQL_OBJECT = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(?:UNIQUE\s+)?(TABLE|VIEW|INDEX)\s+"
                         r"(?:IF\s+NOT\s+EXISTS\s+)?([\w.\"`\[\]]+)", re.I)


def _sql_pieces(source: str) -> list[dict]:
    """Tables, views and indexes, plus queries and changes without parameters (SELECT, UPDATE, DELETE,
    INSERT ... SELECT). Plain INSERT ... VALUES rows are data, so they're not pieces. A "-- name: x" comment names a query."""
    m = _mask(source, "sql")
    found, last, counts = [], 0, {}
    for end in [i for i, c in enumerate(m) if c == ";"] + ([len(m)] if m[m.rfind(";") + 1:].strip() else []):
        text = m[last:end]
        start = last + len(text) - len(text.lstrip())
        head = " ".join(text.split())
        before = source[last:start]
        last = end + 1
        if not head:
            continue
        obj = _SQL_OBJECT.match(" ".join(source[start:end].split()))  # the real text: quoted names are blanked in the mask
        named = re.findall(r"--\s*name:\s*([\w-]+)", before)
        verb = head.split()[0].upper()
        if obj:
            kind, name = obj[1].lower(), re.sub(r"[\"`\[\]]", "", obj[2]).split(".")[-1]
        elif verb in ("SELECT", "WITH", "UPDATE", "DELETE") or (verb == "INSERT" and re.search(r"\bSELECT\b", head, re.I)):
            if re.search(r"\?|(?<![:\w]):\w|\$\d|@\w", head):  # needs values from the app
                continue
            kind = "query" if verb in ("SELECT", "WITH") else "change"
            counts[kind] = counts.get(kind, 0) + 1
            name = named[-1].replace("-", "_") if named else f"{kind}_{counts[kind]}"
        else:
            continue
        found.append({"name": name, "start": start, "open": start, "end": min(end + 1, len(source)), "kind": kind})
    return found


def find(source: str, language: str) -> list[dict]:
    """Every piece of one file: [{name, start, end, ...}] in order, with names made unique (overloads get _2, _3)."""
    found = {"sql": _sql_pieces, "css": _css_pieces, "html": _html_pieces}.get(language, lambda s: _brace_pieces(s, language))(source)
    if language != "sql":  # an empty piece can't be told apart from the empty start, so there's nothing to rebuild
        masked = _html_mask(source) if language == "html" else _mask(source, language)
        inner = lambda f: masked[f["open"] + 1:f["end"]].rsplit("<" if language == "html" else "}", 1)[0]  # noqa: E731
        found = [f for f in found if re.sub(r"<!--.*?-->", "", inner(f), flags=re.S).strip()]
    seen: dict[str, int] = {}
    for f in found:
        seen[f["name"]] = seen.get(f["name"], 0) + 1
        if seen[f["name"]] > 1:
            f["name"] = f"{f['name']}_{seen[f['name']]}"
    return found


def spans(source: str, language: str) -> dict[str, tuple[int, int]]:
    return {f["name"]: (f["start"], f["end"]) for f in find(source, language)}


def signature(source: str, piece: dict, language: str) -> str:
    """What the task shows as the thing to write: the function's header, the selector, the tag, the statement kind."""
    if language == "sql":
        return {"table": f"CREATE TABLE {piece['name']}", "view": f"CREATE VIEW {piece['name']}", "index": f"CREATE INDEX {piece['name']}",
                "query": f"query {piece['name']}", "change": f"change {piece['name']}"}[piece["kind"]]
    if language == "html":
        return " ".join(source[piece["start"]:piece["open"] + 1].split())
    return " ".join(source[piece["start"]:piece["open"]].split())


def stub(source: str, piece: dict, language: str) -> str:
    """The empty version the learner starts from: the header stays, the body is theirs to write."""
    if language == "sql":
        return {"table": f"CREATE TABLE {piece['name']} (\n  -- Your columns here\n);",
                "view": f"CREATE VIEW {piece['name']} AS\n-- Your query here\n;",
                "index": f"-- Your CREATE INDEX {piece['name']} statement here\n;"}.get(piece["kind"], "-- Your statement here\n;")
    head = source[piece["start"]:piece["open"] + 1]
    line_start = source.rfind("\n", 0, piece["start"]) + 1
    indent = re.match(r"[ \t]*", source[line_start:])[0]
    if language == "html":
        return f"{head}\n{indent}  <!-- Your code here -->\n{indent}</{piece['tag']}>"
    if language == "css":
        return f"{head}\n{indent}  /* Your code here */\n{indent}}}"
    body = {"javascript": 'throw new Error("Not written yet");', "typescript": 'throw new Error("Not written yet");',
            "java": 'throw new UnsupportedOperationException("Not written yet");', "rust": "todo!()"}.get(language, "")
    inner = f"{indent}    // Your code here" + (f"\n{indent}    {body}" if body else "")
    return f"{head}\n{inner}\n{indent}}}"


def assemble(source: str, language: str, snippets: dict[str, str]) -> str:
    """The file with the learner's pieces swapped in for the originals (bottom-up keeps the offsets valid)."""
    found = spans(source, language)
    for name in sorted((n for n in snippets if n in found), key=lambda n: found[n][0], reverse=True):
        start, end = found[name]
        code = snippets[name].strip("\n")
        if language == "sql" and not _mask(code, "sql").rstrip().endswith(";"):  # the next statement must stay separate
            code += ";"
        source = source[:start] + code + source[end:]
    return source


def code_of(source: str, language: str, name: str) -> str | None:
    span = spans(source, language).get(name)
    return source[span[0]:span[1]] if span else None


# ---- How pieces use each other: a name followed by ( for code, a table name for SQL ------------------------------

def uses(body: str, language: str, names: set[str]) -> set[str]:
    """Which of `names` this piece's code calls (or, in SQL, reads)."""
    text = _mask(body, language) if language not in ("html",) else body
    if language == "sql":
        return {n for n in names if re.search(rf"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+[\"`\[]?{re.escape(n)}\b", text, re.I)}
    if language in ("css", "html"):
        return set()
    short = {n.split("::")[-1].removesuffix("_2"): n for n in names}
    return {full for s, full in short.items() if re.search(rf"(?<![\w$]){re.escape(s)}\s*(?:<[^<>()]*>)?\s*\(", text)}


# ---- Checks ----------------------------------------------------------------------------------------------------

def _lines(out: str) -> dict[str, str]:
    """{label: value} from a check program's output: one "label: value" per line."""
    found = {}
    for line in out.splitlines():
        label, sep, value = line.partition(": ")
        if sep and label.strip():
            found[label.strip()] = value.strip()
    return found


def compare(expected: dict[str, str], got: dict[str, str] | None, error: str = "") -> list[dict]:
    """One result per label of the original's output."""
    if got is None:
        return [{"name": label, "passed": False, "message": error or "It didn't run."} for label in expected]
    return [{"name": label, "passed": got.get(label) == value,
             "message": None if got.get(label) == value else
             (f"Nothing printed for this check." if label not in got else f"Expected: {value}\nGot: {got[label]}")}
            for label, value in expected.items()]


def _replace(source: str, language: str, name: str, snippet: str) -> str:
    return assemble(source, language, {name: snippet})


# CSS: the declarations of the learner's rule against the original's.
def _decls(rule: str) -> dict[str, str]:
    body = _mask(rule, "css")
    open_, close = body.find("{"), body.rfind("}")
    inner = rule[open_ + 1:close if close > open_ else len(rule)]
    out = {}
    for part in re.sub(r"/\*.*?\*/", "", inner, flags=re.S).split(";"):
        prop, sep, value = part.partition(":")
        if sep and prop.strip():
            out[prop.strip().lower()] = re.sub(r"\s*,\s*", ",", " ".join(value.split())).lower()
    return out


def check_css(original: str, mine: str) -> list[dict]:
    want, got = _decls(original), _decls(mine)
    head = lambda r: " ".join(r[:_mask(r, "css").find("{")].split())  # noqa: E731
    results = [{"name": "Keeps the selector", "passed": head(original) == head(mine),
                "message": None if head(original) == head(mine) else f"The rule should stay `{head(original)}`."}]
    for prop, value in want.items():
        ok = got.get(prop) == value
        results.append({"name": f"Sets {prop}", "passed": ok,
                        "message": None if ok else f"{prop} is missing." if prop not in got else f"{prop} has a different value."})
    extra = sorted(set(got) - set(want))
    results.append({"name": "Nothing the original doesn't set", "passed": not extra,
                    "message": f"Not in the original: {', '.join(extra)}." if extra else None})
    return results


# HTML: the same elements, attributes and text, in the same order.
class _Events(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.attrs, self.text = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(f"<{tag}>")
        self.attrs.append(f"<{tag}> " + " ".join(f'{k}="{v}"' for k, v in sorted(attrs) if v is not None or k))

    def handle_endtag(self, tag):
        self.tags.append(f"</{tag}>")

    def handle_data(self, data):
        if data.strip():
            self.text.append(" ".join(data.split()))


def _events(html: str) -> _Events:
    parser = _Events()
    parser.feed(re.sub(r"<!--.*?-->", "", html, flags=re.S))
    parser.close()
    return parser


def check_html(original: str, mine: str) -> list[dict]:
    want, got = _events(original), _events(mine)

    def first_difference(a: list[str], b: list[str]) -> str:
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return f"Expected {x}\nGot {y}"
        return f"Expected {len(a)} of them, got {len(b)}."

    return [{"name": what, "passed": a == b, "message": None if a == b else first_difference(a, b)}
            for what, a, b in (("Same elements, in the same order", want.tags, got.tags),
                               ("Same attributes", want.attrs, got.attrs), ("Same text", want.text, got.text))]


# SQL: run every .sql file in order on an empty SQLite database, with the learner's statement in place of the original.
def sql_files(root: Path) -> list[Path]:
    """Schema files first, then data, then the rest; numbered files (001_init.sql) keep their order."""
    rank = lambda p: 0 if re.search(r"schema|create|init|ddl|table|migration", p.name, re.I) else 1 if re.search(r"seed|data|insert|fixture", p.name, re.I) else 2  # noqa: E731
    return sorted((p for p in root.rglob("*.sql") if not {"node_modules", ".git"} & set(p.parts)), key=lambda p: (rank(p), str(p)))


def _statements(source: str) -> list[str]:
    m = _mask(source, "sql")
    out, last = [], 0
    for i, c in enumerate(m + ";"):
        if c == ";":
            if m[last:i].strip():  # from its first real character: comments before it aren't part of it
                out.append(source[last + len(m[last:i]) - len(m[last:i].lstrip()):i].strip())
            last = i + 1
    return out


def _sql_run(root: Path, file: str, target: str | None) -> tuple[sqlite3.Connection, dict, list[str]]:
    """Runs everything. Returns (database, {"rows", "columns", "error"} for the target statement, failed statements)."""
    db = sqlite3.connect(":memory:")
    seen, failed = {}, []
    for path in sql_files(root):
        rel = str(path.relative_to(root))
        source = target if (rel == file and target is not None) else path.read_text(errors="replace")
        for statement in _statements(source):
            try:
                cursor = db.execute(statement)
                if cursor.description:
                    seen[statement] = {"columns": [d[0] for d in cursor.description], "rows": cursor.fetchall()}
            except sqlite3.Error as err:
                failed.append(f"{statement[:60]}: {err}")
                seen[statement] = {"error": str(err)}
    return db, seen, failed


def _table(db: sqlite3.Connection, name: str) -> dict:
    try:
        return {"columns": [r[1] for r in db.execute(f'PRAGMA table_info("{name}")')],
                "types": [(r[1], r[2].upper(), r[3], r[4], r[5]) for r in db.execute(f'PRAGMA table_info("{name}")')],
                "keys": sorted(map(str, db.execute(f'PRAGMA foreign_key_list("{name}")').fetchall())),
                "rows": sorted(map(repr, db.execute(f'SELECT * FROM "{name}"').fetchall()))}
    except sqlite3.Error as err:
        return {"error": str(err)}


def check_sql(root: Path, file: str, name: str, kind: str, snippet: str) -> list[dict]:
    """Compares what the database looks like (or what the query returns) with the original's."""
    source = (root / file).read_text(errors="replace")
    original_code = code_of(source, "sql", name)
    db0, seen0, failed0 = _sql_run(root, file, None)
    mine_file = _replace(source, "sql", name, snippet)
    db1, seen1, failed1 = _sql_run(root, file, mine_file)
    new_errors = [f for f in failed1 if f not in failed0]
    results = []
    if kind in ("table", "view"):
        a, b = _table(db0, name), _table(db1, name)
        if "error" in b:
            return [{"name": f"Creates {name}", "passed": False, "message": b["error"]}]
        checks = [("Same columns, in the same order", "columns")]
        if kind == "table":
            checks += [("Same types, keys and rules", "types"), ("Same links to other tables", "keys")]
        checks += [("Same rows" if kind == "view" else "The data still loads into it", "rows")]
        results = [{"name": label, "passed": a.get(key) == b.get(key),
                    "message": None if a.get(key) == b.get(key) else f"Expected: {a.get(key)}\nGot: {b.get(key)}"[:600]}
                   for label, key in checks]
    elif kind == "index":
        info = lambda db: (db.execute(f'PRAGMA index_info("{name}")').fetchall(), [r[2] for r in db.execute("PRAGMA index_list(sqlite_master)")])  # noqa: E731
        a = [r[2] for r in db0.execute(f'PRAGMA index_info("{name}")')]
        b = [r[2] for r in db1.execute(f'PRAGMA index_info("{name}")')]
        results = [{"name": "Indexes the same columns", "passed": a == b, "message": None if a == b else f"Expected: {a}\nGot: {b}"}]
    else:
        mine_code = (_statements(snippet) or [""])[0]
        want = seen0.get((_statements(original_code) or [""])[0], {})
        got = seen1.get(mine_code, {"error": "Your statement didn't run."})
        if kind == "query":
            if "error" in got:
                return [{"name": "Runs", "passed": False, "message": got["error"]}]
            ordered = bool(re.search(r"\bORDER\s+BY\b", original_code, re.I))
            rows = lambda r: r if ordered else sorted(map(repr, r))  # noqa: E731
            results = [{"name": "Same column names", "passed": want.get("columns") == got.get("columns"),
                        "message": None if want.get("columns") == got.get("columns") else f"Expected: {want.get('columns')}\nGot: {got.get('columns')}"},
                       {"name": "Same rows" + (", in the same order" if ordered else ""),
                        "passed": rows(want.get("rows", [])) == rows(got.get("rows", [])),
                        "message": None if rows(want.get("rows", [])) == rows(got.get("rows", [])) else
                        f"Expected {len(want.get('rows', []))} rows, starting {want.get('rows', [])[:3]}\nGot {len(got.get('rows', []))}, starting {got.get('rows', [])[:3]}"}]
        else:
            tables = [r[0] for r in db0.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for t in tables:
                a, b = _table(db0, t), _table(db1, t)
                results.append({"name": f"Leaves {t} the same as the original", "passed": a == b,
                                "message": None if a == b else f"Expected {len(a.get('rows', []))} rows, got {len(b.get('rows', []))}"})
    if new_errors and all(r["passed"] for r in results):
        results.append({"name": "The rest of the files still run", "passed": False, "message": new_errors[0]})
    return results


def sql_kind(root: Path, file: str, name: str) -> str:
    return next(p["kind"] for p in _sql_pieces((root / file).read_text(errors="replace")) if p["name"] == name)


# Code: run a check program on a copy of the project.
def program(language: str, file_code: str, check: str) -> tuple[str, dict]:
    """(the target file's new text, extra files) with the check program added the way each language needs it."""
    if language in ("javascript", "typescript"):
        return f"{file_code}\n\n// ---- Carve-Out check ----\n{check}\n", {}
    if language in ("c", "cpp"):
        code = re.sub(r"\b(int|void)(\s+)main(\s*\()", r"\1\2carve_project_main\3", file_code)
        return f"{code}\n\n/* ---- Carve-Out check ---- */\n{check}\nint main(void) {{ return carve_check(); }}\n", {}
    if language == "rust":
        code = re.sub(r"(?m)^(\s*)(pub\s+)?fn\s+main\s*\(", r"\1#[allow(dead_code)]\n\1\2fn carve_project_main(", file_code)
        return f"{code}\n\n// ---- Carve-Out check ----\n{check}\n", {}
    if language == "java":
        return file_code, {"CarveCheck.java": check}
    raise ValueError(language)


def _java_main(check: str) -> str:
    package = re.search(r"^\s*package\s+([\w.]+)\s*;", check, re.M)
    return f"{package[1]}.CarveCheck" if package else "CarveCheck"


def _run(cmd: list[str], cwd: Path) -> tuple[bool, str, str]:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "", f"It ran for more than {TIMEOUT} seconds. Is there a loop that never ends?"
    except FileNotFoundError:
        return False, "", f"{cmd[0]} isn't installed on this computer."
    return out.returncode == 0, out.stdout, out.stderr


def run_local(root: Path, file: str, language: str, file_code: str, check: str) -> tuple[bool, str, str]:
    """Runs the check program on a copy of the project with `file` replaced. (ok, output, errors)."""
    code, extra = program(language, file_code, check)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp, root.name)
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "target", "*.class", "__pycache__"))
        (copy / file).write_text(code)
        for name, text in extra.items():
            (copy / name).write_text(text)
        target = copy / file
        if language == "javascript":
            return _run(["node", str(target)], target.parent)
        if language == "typescript":  # Node with TypeScript built in, else tsx (downloaded once by npx)
            ok, out, err = _run(["node", "--experimental-strip-types", "--no-warnings", str(target)], target.parent)
            if "ERR_NO_TYPESCRIPT" in err or "Unknown file extension" in err:
                return _run(["npx", "--yes", "tsx@4.19.2", str(target)], target.parent)
            return ok, out, err
        if language in ("c", "cpp"):
            ext = (".c",) if language == "c" else (".cpp", ".cc", ".cxx")
            others = [p for p in copy.rglob("*") if p.suffix in ext and p != target and not {"test", "tests", "examples", "build"} & set(p.relative_to(copy).parts)
                      and not re.search(r"\b(int|void)\s+main\s*\(", p.read_text(errors="replace"))]
            compiler = ["gcc", "-std=gnu11"] if language == "c" else ["g++", "-std=gnu++17"]
            ok, out, err = _run([*compiler, "-w", "-O0", f"-I{copy}", f"-I{target.parent}", str(target), *map(str, others), "-o", str(Path(tmp, "check")), "-lm"], copy)
            return (_run([str(Path(tmp, "check"))], copy) if ok else (False, out, err))
        if language == "java":
            sources = [str(p) for p in copy.rglob("*.java") if not {"test", "tests"} & set(p.relative_to(copy).parts)]
            ok, out, err = _run(["javac", "-nowarn", "-encoding", "UTF-8", "-d", str(Path(tmp, "out")), *sources], copy)
            return (_run(["java", "-cp", str(Path(tmp, "out")), _java_main(check)], copy) if ok else (False, out, err))
        if language == "rust":
            ok, out, err = _run(["rustc", "--edition", "2021", "-A", "warnings", str(target), "-o", str(Path(tmp, "check"))], target.parent)
            return (_run([str(Path(tmp, "check"))], copy) if ok else (False, out, err))
    raise ValueError(language)


async def run_browser(root: Path, file: str, language: str, file_code: str, check: str) -> tuple[bool, str, str]:
    """JavaScript and TypeScript in the browser: the page runs them in a throwaway worker (web/python.js, runJs)."""
    from js import runJs
    code, _ = program(language, file_code, check)
    files = {str(p.relative_to(root)): p.read_text(errors="replace") for p in root.rglob("*")
             if p.is_file() and p.suffix in (".js", ".mjs", ".ts", ".json") and "node_modules" not in p.parts}
    files[file] = code
    reply = json.loads(await runJs(json.dumps({"files": files, "entry": file, "lang": language, "timeout": TIMEOUT * 1000})))
    return reply["ok"], reply.get("out", ""), reply.get("error", "")


WANDBOX = {"c": "gcc-13.2.0-c", "cpp": "gcc-13.2.0", "java": "openjdk-jdk-22+36", "rust": "rust-1.82.0"}


def wandbox_job(root: Path, file: str, language: str, file_code: str, check: str) -> dict:
    """The request for Wandbox (https://wandbox.org): the target file with its check program as the main file, plus
    what it needs from the project. Java is merged into one file, the check class first, since Java runs the first class."""
    code, extra = program(language, file_code, check)
    target = Path(file)
    files = {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file() and p.stat().st_size < 200_000
             and not {".git", "node_modules", "target", "build", "test", "tests"} & set(p.relative_to(root).parts)}
    if language == "java":
        packages = {m for p in files.values() if p.suffix == ".java" for m in re.findall(r"^\s*package\s+([\w.]+)\s*;", p.read_text(errors="replace"), re.M)}
        texts = [extra["CarveCheck.java"]] + [code if rel == file else p.read_text(errors="replace") for rel, p in files.items() if p.suffix == ".java"]
        imports, bodies = [], []
        for text in texts:
            text = re.sub(r"(?m)^\s*package\s+[\w.]+\s*;", "", text)
            for imp in re.findall(r"(?m)^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", text):
                if not any(imp.startswith(pk + ".") for pk in packages) and f"import {imp};" not in imports:
                    imports.append(f"import {imp};")
            text = re.sub(r"(?m)^\s*import\s+(?:static\s+)?[\w.*]+\s*;", "", text)
            bodies.append(re.sub(r"(?m)^public\s+((?:abstract\s+|final\s+|sealed\s+)*(?:class|interface|enum|record)\b)", r"\1", text))
        return {"compiler": WANDBOX[language], "code": "\n".join(imports) + "\n" + "\n".join(bodies)}
    if language == "rust":  # modules are found next to the main file
        base = target.parent
        codes = [{"file": str(Path(rel).relative_to(base)), "code": p.read_text(errors="replace")} for rel, p in files.items()
                 if p.suffix == ".rs" and rel != file and Path(rel).is_relative_to(base)]
        return {"compiler": WANDBOX[language], "code": code, "codes": codes, "compiler-option-raw": "--edition=2021\n-Awarnings"}
    ext = (".c",) if language == "c" else (".cpp", ".cc", ".cxx")
    others = [rel for rel, p in files.items() if p.suffix in ext and rel != file
              and not re.search(r"\b(int|void)\s+main\s*\(", p.read_text(errors="replace"))]
    codes = [{"file": rel, "code": p.read_text(errors="replace")} for rel, p in files.items()
             if p.suffix in (".h", ".hpp", ".hh", ".inc") or rel in others]
    options = others + ["-I.", f"-I{target.parent}" if str(target.parent) != "." else "-I.", "-w", "-lm"]
    return {"compiler": WANDBOX[language], "code": code, "codes": codes, "compiler-option-raw": "\n".join(options)}


async def run_online(root: Path, file: str, language: str, file_code: str, check: str) -> tuple[bool, str, str]:
    """Java, C, C++ and Rust where there's no compiler (the browser): compiled and run on Wandbox. (ok, output, errors)."""
    body = json.dumps(wandbox_job(root, file, language, file_code, check))
    url = "https://wandbox.org/api/compile.json"
    try:
        if in_browser():
            from pyodide.http import pyfetch
            reply = await pyfetch(url, method="POST", headers={"Content-Type": "application/json"}, body=body)
            if not reply.ok:
                raise RuntimeError(str(reply.status))
            data = await reply.json()
        else:
            import urllib.request

            def post():
                request = urllib.request.Request(url, body.encode(), {"Content-Type": "application/json", "User-Agent": "carve-out-tutor"})
                with urllib.request.urlopen(request, timeout=60) as r:
                    return json.load(r)
            data = await asyncio.to_thread(post)
    except Exception:
        return False, "", f"The online compiler ({ONLINE}) couldn't be reached. Check your connection and try again."
    if data.get("compiler_error") and str(data.get("status")) != "0" and not data.get("program_output"):
        return False, "", data["compiler_error"]
    return str(data.get("status")) == "0", data.get("program_output", ""), data.get("program_error", "") or data.get("compiler_error", "")


async def run(root: Path, file: str, language: str, file_code: str, check: str) -> tuple[bool, str, str]:
    if in_browser():
        if language in ("javascript", "typescript"):
            return await run_browser(root, file, language, file_code, check)
        return await run_online(root, file, language, file_code, check)
    ok, out, err = await asyncio.to_thread(run_local, root, file, language, file_code, check)
    if language in WANDBOX and "isn't installed on this computer" in err:  # no compiler here: use the online one
        return await run_online(root, file, language, file_code, check)
    return ok, out, err


def _short(text: str, lines: int = 8) -> str:
    return "\n".join(text.strip().splitlines()[-lines:]) or "(no message)"


_EXPECTED: dict = {}


async def check_code(root: Path, file: str, name: str, check: str, snippet: str) -> list[dict]:
    """Runs the check program on the original and on the learner's version; every printed line must match."""
    language = lang(file)
    source = (root / file).read_text(errors="replace")
    key = (str(root), file, source, check)
    if key not in _EXPECTED:  # the original never changes, so it runs once per check program
        ok, out, err = await run(root, file, language, source, check)
        _EXPECTED[key] = (ok, out, err)
    ok, out, err = _EXPECTED[key]
    expected = _lines(out)
    if not ok or not expected:
        return [{"name": "the checks", "passed": False, "message": "The checks don't run on the original code: " + _short(err or out)}]
    ok, out, err = await run(root, file, language, _replace(source, language, name, snippet), check)
    return compare(expected, _lines(out) if ok else None, _short(err or out))


async def check(root: Path, file: str, name: str, snippet: str, check_program: str = "") -> list[dict]:
    """The results for the learner's version of one piece: [{name, passed, message}], like the pytest results."""
    language = lang(file)
    if language in CODE:
        return await check_code(root, file, name, check_program, snippet)
    source = (root / file).read_text(errors="replace")
    original = code_of(source, language, name) or ""
    if language == "css":
        return check_css(original, snippet)
    if language == "html":
        return check_html(original, snippet)
    if language == "sql":
        return check_sql(root, file, name, sql_kind(root, file, name), snippet)
    raise ValueError(language)


if __name__ == "__main__":
    js = """import { tax } from './tax.js';
// a comment with a { brace
export function total(items) {
  const s = "}";
  return items.reduce((a, b) => a + b, 0) + tax(1);
}
const avg = (xs) => {
  if (!xs.length) { return 0; }
  return total(xs) / xs.length;
};
class Cart {
  add(item) { this.items.push(item); }
  static empty() { return new Cart(); }
}
"""
    assert [f["name"] for f in find(js, "javascript")] == ["total", "avg", "add", "empty"], find(js, "javascript")
    assert uses(code_of(js, "javascript", "avg"), "javascript", {"total", "avg", "add"}) == {"total"}
    assert "throw new Error" in stub(js, find(js, "javascript")[0], "javascript")
    c = """#include <stdio.h>
static int add(int a, int b) { return a + b; }
int sum(const int *xs, int n) {
    int s = 0;
    for (int i = 0; i < n; i++) { s = add(s, xs[i]); }
    return s;
}
int main(void) { printf("%d\\n", sum((int[]){1, 2}, 2)); return 0; }
"""
    assert [f["name"] for f in find(c, "c")] == ["add", "sum", "main"]
    assert code_of(c, "c", "add").startswith("static int add"), code_of(c, "c", "add")
    assert code_of("import x from './x'\nexport function f(a) {\n  return a\n}\n", "javascript", "f").startswith("export function f")
    java = """package bank;
public class Account {
    private long cents;
    @Override
    public String toString() { return "Account"; }
    public void deposit(long amount) throws IllegalArgumentException {
        if (amount <= 0) { throw new IllegalArgumentException("no"); }
        Runnable r = new Runnable() { public void run() { } };
        cents += amount;
    }
    public Account(long start) { cents = start; }
}
"""
    assert [f["name"] for f in find(java, "java")] == ["toString", "deposit", "Account"], find(java, "java")
    rust = "struct P { x: i32 }\nimpl P {\n    fn norm<'a>(&'a self) -> i32 { if self.x > 0 { self.x } else { -self.x } }\n}\nfn main() { let c = '{'; }\n"
    assert [f["name"] for f in find(rust, "rust")] == ["norm", "main"]
    ts = "export function greet(name: string): string {\n  return `hi ${name}`;\n}\nconst f = async (x: number): Promise<number> => {\n  return x;\n};\n"
    assert [f["name"] for f in find(ts, "typescript")] == ["greet", "f"], find(ts, "typescript")
    css = "/* top */\n.header nav a { color: red; }\n@media (max-width: 600px) {\n  .header { display: none; }\n}\n"
    assert [f["name"] for f in find(css, "css")] == [".header nav a", ".header"]
    assert all(r["passed"] for r in check_css(".a { color: red; gap: 1px }", ".a {\n  gap: 1px;\n  color: RED;\n}"))
    assert not check_css(".a { color: red }", ".a { color: blue }")[1]["passed"]
    html = '<body>\n<nav id="menu"><a href="/">Home</a><div id="inner"></div></nav>\n<!-- <p id="x"></p> -->\n<main id="main"><p>Hi</p></main>\n</body>'
    assert [f["name"] for f in find(html, "html")] == ["menu", "main"]
    assert [f["name"] for f in find('<ul id="list"></ul><p id="p">Hi</p><img id="i" src="x">', "html")] == ["p"]
    assert [f["name"] for f in find("function noop() {}\nfunction one() { return 1; }", "javascript")] == ["one"]
    assert all(r["passed"] for r in check_html('<main id="m"><p>Hi  there</p></main>', '<main id="m">\n  <p>Hi there</p>\n</main>'))
    sql = "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);\nINSERT INTO users VALUES (1, 'a;b');\n-- name: user_names\nSELECT name FROM users ORDER BY name;\nSELECT * FROM users WHERE id = ?;\n"
    assert [(f["name"], f["kind"]) for f in find(sql, "sql")] == [("users", "table"), ("user_names", "query")]
    assert [f["name"] for f in find('CREATE UNIQUE INDEX "Article_slug_key" ON "Article"("slug");', "sql")] == ["Article_slug_key"]
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "schema.sql").write_text(sql)
        assert all(r["passed"] for r in check_sql(Path(tmp), "schema.sql", "user_names", "query", "SELECT name FROM users ORDER BY name"))
        assert not check_sql(Path(tmp), "schema.sql", "user_names", "query", "SELECT id FROM users")[0]["passed"]
        assert all(r["passed"] for r in check_sql(Path(tmp), "schema.sql", "users", "table", "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);"))
        assert not all(r["passed"] for r in check_sql(Path(tmp), "schema.sql", "users", "table", "CREATE TABLE users (id INTEGER, name TEXT);"))
    assert assemble(js, "javascript", {"total": "function total(items) { return 0; }"}).count("return 0;") == 2
    print("langs ok")
