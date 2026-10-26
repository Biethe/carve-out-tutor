"""Cards and tests for the functions that have no hand-written card, written by the learner's AI the first time one
is opened, then kept in data/cards/. A generated test file is only kept if it passes on the original code and fails
on the empty stub, so a bad AI-written test can never fail the learner unfairly."""
import json
import re
from pathlib import Path

from tutor import langs, llm, overview, pieces, progress, runner
from tutor.pieces import PIECES, assemble, reference_code


def _path(piece: str, name: str, suffix: str) -> Path:
    return progress.work() / "cards" / f"{piece}.{re.sub(r'[^\w.-]', '_', name)}{suffix}"  # CSS selectors make odd names


def check_program(piece: str, name: str) -> str:
    """The check program of a piece in another language (tutor/langs.py), or "" (SQL, CSS and HTML need none)."""
    path = _path(piece, name, ".check")
    return path.read_text() if path.exists() else ""


def load(piece: str, name: str) -> dict | None:
    path = _path(piece, name, ".json")
    return json.loads(path.read_text()) if path.exists() else None


def _test_name(piece: str, name: str) -> str:
    return f"test_{piece.replace('.', '_')}_{name}.py"  # a dot in a test file's name would break its import


def test_file(piece: str, name: str) -> tuple[str, str]:
    return _test_name(piece, name), _path(piece, name, ".py").read_text()


def _other_facts(piece: str, name: str) -> dict:
    """facts() for the other languages: callers and what it uses are found by name (tutor/langs.py)."""
    texts = {}
    for key, p in PIECES.items():
        if p.get("lang"):
            source = (pieces.STORE / p["file"]).read_text(errors="replace")
            texts.update({(key, n): (p["lang"], t) for n, t in pieces.function_texts(p["file"], source).items()})
    language, body = texts[(piece, name)]
    verb = "reads" if language == "sql" else "calls"
    callers = [k for k, (lang, text) in texts.items() if k != (piece, name) and langs.uses(text, lang, {name})]
    used = [k for k in texts if k != (piece, name) and k[1] in langs.uses(body, language, {n for _, n in texts})]
    return {"call_sites": [f"{PIECES[k]['file']} ({n}) {verb} it." for k, n in callers[:6]] or ["Nothing else in the project uses it directly."],
            "references": [(PIECES[k]["file"], n) for k, n in (callers or used)[:3]], "route": None}


def facts(piece: str, name: str) -> dict:
    """What the code itself says about a function: who calls it, which request runs it, and the callers' code."""
    if PIECES[piece].get("lang"):
        return _other_facts(piece, name)
    p = overview.Project()
    module = ".".join(Path(PIECES[piece]["file"]).with_suffix("").parts)
    callers = [(m, n) for (m, n), fn in p.funcs.items() for cm, cn, _ in p.calls(m, fn) if (cm, cn) == (module, name) and (m, n) != (module, name)]
    route = next((f"{verb} {path}" for verb, path, m, fn in p.routes() if (m, fn.name) == (module, name)), None)
    call_sites = [f"{p.path(m)} ({n}) calls it." for m, n in callers]
    if route:
        call_sites.insert(0, f"It runs when the browser sends {route}.")
    # Code to read: who calls it; if nothing does (a route the browser triggers), what it uses instead.
    uses = [(cm, cn) for cm, cn, _ in p.calls(module, p.funcs[(module, name)]) if (cm, cn) != (module, name)]
    reads = callers or list(dict.fromkeys(uses))
    return {"call_sites": call_sites or ["Nothing else in the project calls it directly."],
            "references": [(p.path(m), n) for m, n in reads[:3]], "route": route}


def notes() -> str:
    """How this project is tested, for the AI writing the tests: Polyvault's specifics, or what kind of upload it is."""
    if pieces.STORE == pieces.BUILTIN:
        return llm.STORE_NOTES
    from tutor import projects
    kind = projects.kind(pieces.STORE)
    return {
        "wsgi": f"- A Flask app (the app object is `{kind.get('var')}` in module `{kind.get('module')}`).\n"
                "- Plain functions: call them directly. A route: call it inside "
                f"`with {kind.get('var')}.test_request_context(path, method=..., data={{...}}):` and check the response.",
        "asgi": "- A FastAPI/Starlette app. Plain functions: call them directly. For a route, prefer testing the plain "
                "functions it relies on; if you must call the route, pass simple fake arguments.",
        "static": "- A web page: Python files here are helpers. Call their functions directly.",
        "tests": "- A Python library or script: call its functions directly.",
    }[kind["kind"]] + "\n- Files the project reads or writes are relative to its folder; tests run from a copy of it."


async def _prepare_other(piece: str, name: str) -> str | None:
    """prepare() for the other languages. Code gets a check program, kept only if it runs on the original and an
    empty version fails it. SQL, CSS and HTML are compared with the original directly, so only the card is written."""
    file, language = PIECES[piece]["file"], PIECES[piece]["lang"]
    base = next(f for f in PIECES[piece]["functions"] if f["name"] == name)
    known = facts(piece, name)
    source = (pieces.STORE / file).read_text(errors="replace")
    original = reference_code(file, name)
    context = {"lang": language, "file": file, "source": source[:14000], "function": original, "call_sites": known["call_sites"],
               "callers": "\n\n".join(reference_code(f, n) for f, n in known["references"])}
    problem = ""
    for _ in range(2 if language in langs.CODE else 1):  # one retry, told what went wrong
        card = await llm.card_other(language, context, problem)
        if card is None:
            return llm.BUSY
        on_original = await langs.check(pieces.STORE, file, name, original, card["check"])
        on_stub = await langs.check(pieces.STORE, file, name, base["stub"], card["check"])
        failing = [f"{r['name']}: {r['message']}" for r in on_original if not r["passed"]]
        if failing:
            problem = "The check program FAILED on the original, correct code, so it's wrong:\n" + "\n".join(failing)[:1500]
        elif all(r["passed"] for r in on_stub):
            problem = "Every line printed the same when the function was empty, so the checks don't test it."
        else:
            _path(piece, name, "").parent.mkdir(parents=True, exist_ok=True)
            if card["check"]:
                _path(piece, name, ".check").write_text(card["check"])
            _path(piece, name, ".json").write_text(json.dumps({
                "description": card["description"], "breaks": card["breaks"], "question": card["question"], "answer": card["answer"],
                "call_sites": known["call_sites"], "references": known["references"],
                "criteria": [(r["name"], r["name"]) for r in on_original]}, indent=2))
            return None
    if language not in langs.CODE:
        return f"Chip can't check this {langs.NAMES[language]} piece here (it doesn't run the same way in this checker), so it stays the original code."
    return "Chip couldn't write reliable checks for this one, so it stays the original code for now."


async def prepare(piece: str, name: str) -> str | None:
    """Writes the card and tests if they aren't there yet. Returns None when ready, or why it couldn't be done."""
    if load(piece, name):
        return None
    if PIECES[piece].get("lang"):
        return await _prepare_other(piece, name)
    file = PIECES[piece]["file"]
    base = next(f for f in PIECES[piece]["functions"] if f["name"] == name)
    known = facts(piece, name)
    context = {"notes": notes(), "file": file, "source": (pieces.STORE / file).read_text(), "function": reference_code(file, name),
               "call_sites": known["call_sites"],
               "callers": "\n\n".join(reference_code(f, n) for f, n in known["references"])}
    original = (pieces.STORE / file).read_text()
    stubbed = assemble(piece, {name: base["stub"]})
    problem = ""
    for _ in range(2):  # one retry, told what went wrong
        card = await llm.card(piece, name, context, problem)
        if card is None:
            return llm.BUSY
        test_name = _test_name(piece, name)
        on_original = await runner.run_test_code(file, test_name, card["tests"], original)
        on_stub = await runner.run_test_code(file, test_name, card["tests"], stubbed)
        failing = [f"{r['name']}: {r['message']}" for r in on_original if not r["passed"]]
        if failing:
            problem = "These tests FAILED on the original, correct code, so they're wrong:\n" + "\n".join(failing)
        elif all(r["passed"] for r in on_stub):
            problem = "These tests still PASS when the function only raises NotImplementedError, so they don't test it."
        else:
            names = {r["name"] for r in on_original}
            _path(piece, name, "").parent.mkdir(parents=True, exist_ok=True)
            _path(piece, name, ".py").write_text(card["tests"])
            _path(piece, name, ".json").write_text(json.dumps({
                "description": card["description"], "breaks": card["breaks"], "question": card["question"],
                "answer": card["answer"], "call_sites": known["call_sites"], "references": known["references"],
                "criteria": [(c["test"], c["text"]) for c in card["criteria"] if c["test"] in names]
                            or [(n, n.removeprefix("test_").replace("_", " ")) for n in sorted(names)],
            }, indent=2))
            return None
    return "Chip couldn't write reliable tests for this one, so it stays the original code for now."
