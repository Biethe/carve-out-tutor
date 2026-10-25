"""Cards and tests for the functions that have no hand-written card, written by the learner's AI the first time one
is opened, then kept in data/cards/. A generated test file is only kept if it passes on the original code and fails
on the empty stub, so a bad AI-written test can never fail the learner unfairly."""
import json
from pathlib import Path

from tutor import llm, overview, pieces, progress, runner
from tutor.pieces import PIECES, assemble, reference_code


def _path(piece: str, name: str, suffix: str) -> Path:
    return progress.work() / "cards" / f"{piece}.{name}{suffix}"


def load(piece: str, name: str) -> dict | None:
    path = _path(piece, name, ".json")
    return json.loads(path.read_text()) if path.exists() else None


def _test_name(piece: str, name: str) -> str:
    return f"test_{piece.replace('.', '_')}_{name}.py"  # a dot in a test file's name would break its import


def test_file(piece: str, name: str) -> tuple[str, str]:
    return _test_name(piece, name), _path(piece, name, ".py").read_text()


def facts(piece: str, name: str) -> dict:
    """What the code itself says about a function: who calls it, which request runs it, and the callers' code."""
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


async def prepare(piece: str, name: str) -> str | None:
    """Writes the card and tests if they aren't there yet. Returns None when ready, or why it couldn't be done."""
    if load(piece, name):
        return None
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
