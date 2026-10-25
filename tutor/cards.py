"""Cards and tests for the functions that have no hand-written card, written by the learner's AI the first time one
is opened, then kept in data/cards/. A generated test file is only kept if it passes on the original code and fails
on the empty stub, so a bad AI-written test can never fail the learner unfairly."""
import json
from pathlib import Path

from tutor import llm, overview, runner
from tutor.pieces import PIECES, STORE, assemble, reference_code
from tutor.progress import DATA

DIR = DATA / "cards"


def _path(piece: str, name: str, suffix: str) -> Path:
    return DIR / f"{piece}.{name}{suffix}"


def load(piece: str, name: str) -> dict | None:
    path = _path(piece, name, ".json")
    return json.loads(path.read_text()) if path.exists() else None


def test_file(piece: str, name: str) -> tuple[str, str]:
    return f"test_{piece}_{name}.py", _path(piece, name, ".py").read_text()


def facts(piece: str, name: str) -> dict:
    """What the code itself says about a function: who calls it, which request runs it, and the callers' code."""
    p = overview.Project()
    module = ".".join(Path(PIECES[piece]["file"]).with_suffix("").parts)
    callers = [(m, n) for (m, n), fn in p.funcs.items() for cm, cn, _ in p.calls(m, fn) if (cm, cn) == (module, name) and (m, n) != (module, name)]
    route = next((f"{verb} {path}" for verb, path, m, fn in p.routes() if (m, fn.name) == (module, name)), None)
    call_sites = [f"{p.path(m)} ({n}) calls it." for m, n in callers]
    if route:
        call_sites.insert(0, f"It runs when the browser sends {route}.")
    return {"call_sites": call_sites or ["Nothing else in the project calls it directly."],
            "references": [(p.path(m), n) for m, n in callers[:3]], "route": route}


async def prepare(piece: str, name: str) -> str | None:
    """Writes the card and tests if they aren't there yet. Returns None when ready, or why it couldn't be done."""
    if load(piece, name):
        return None
    file = PIECES[piece]["file"]
    base = next(f for f in PIECES[piece]["functions"] if f["name"] == name)
    known = facts(piece, name)
    context = {"file": file, "source": (STORE / file).read_text(), "function": reference_code(file, name),
               "call_sites": known["call_sites"],
               "callers": "\n\n".join(reference_code(f, n) for f, n in known["references"])}
    original = (STORE / file).read_text()
    stubbed = assemble(piece, {name: base["stub"]})
    problem = ""
    for _ in range(2):  # one retry, told what went wrong
        card = await llm.card(piece, name, context, problem)
        if card is None:
            return llm.BUSY
        test_name = f"test_{piece}_{name}.py"
        on_original = await runner.run_test_code(file, test_name, card["tests"], original)
        on_stub = await runner.run_test_code(file, test_name, card["tests"], stubbed)
        failing = [f"{r['name']}: {r['message']}" for r in on_original if not r["passed"]]
        if failing:
            problem = "These tests FAILED on the original, correct code, so they're wrong:\n" + "\n".join(failing)
        elif all(r["passed"] for r in on_stub):
            problem = "These tests still PASS when the function only raises NotImplementedError, so they don't test it."
        else:
            names = {r["name"] for r in on_original}
            DIR.mkdir(parents=True, exist_ok=True)
            _path(piece, name, ".py").write_text(card["tests"])
            _path(piece, name, ".json").write_text(json.dumps({
                "description": card["description"], "breaks": card["breaks"], "question": card["question"],
                "answer": card["answer"], "call_sites": known["call_sites"], "references": known["references"],
                "criteria": [(c["test"], c["text"]) for c in card["criteria"] if c["test"] in names]
                            or [(n, n.removeprefix("test_").replace("_", " ")) for n in sorted(names)],
            }, indent=2))
            return None
    return "Chip couldn't write reliable tests for this one, so it stays the original code for now."
