"""The tutor app: serves the pages and the JSON API on localhost:8000."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tutor import llm, progress, runner
from tutor.pieces import PIECES, task

PAGES = Path(__file__).parent / "pages"


@asynccontextmanager
async def lifespan(app):
    yield
    runner.stop_store()  # don't leave the store running after the tutor stops


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def catalog():
    return FileResponse(PAGES / "catalog.html")


@app.get("/project")
def project():
    return FileResponse(PAGES / "project.html")


@app.get("/learn")
def learn():
    return FileResponse(PAGES / "learn.html")


@app.get("/api/state")
def state():
    prog = progress.load()
    current = prog["current"]
    result = {
        "current": current,
        "ownership": progress.ownership(prog),
        "passed": progress.passed(prog),
        "all_done": len(progress.passed(prog)) == len(PIECES),
    }
    if current:
        piece = prog["pieces"][current]
        result.update(
            round=list(PIECES).index(current) + 1,
            task=task(current),
            code=piece["draft"] if piece["draft"] is not None else PIECES[current]["stub"],
            status=piece["status"],
            last_results=piece["last_results"],
            check=piece["check"],
        )
    return result


@app.post("/api/round/start")
def round_start():
    """Open the next piece that hasn't passed. Ignored if a round is already open."""
    prog = progress.load()
    current = prog["current"]
    if current and prog["pieces"][current]["status"] != "passed":
        return state()
    remaining = [p for p in PIECES if prog["pieces"][p]["status"] != "passed"]
    if remaining:
        prog["current"] = remaining[0]
        prog["pieces"][remaining[0]]["status"] = "in_progress"
        progress.save(prog)
    return state()


@app.put("/api/code")
def save_code(code: str = Body(embed=True)):
    prog = progress.load()
    piece = prog["pieces"].get(prog["current"])
    if piece and piece["status"] == "in_progress":
        piece["draft"] = code
        progress.save(prog)
    return {"saved": True}


@app.post("/api/submit")
def submit(code: str = Body(embed=True)):
    prog = progress.load()
    current = prog["current"]
    piece = prog["pieces"].get(current)
    if not piece or piece["status"] != "in_progress":
        return {"error": "No open round to submit to."}
    piece["draft"] = code
    results = runner.run_tests(current, code)
    piece["last_results"] = results
    all_passed = all(r["passed"] for r in results)
    if all_passed:
        # Once a piece passes it is the learner's for good: Run project uses this file from now on.
        learner_dir = progress.DATA / "learner"
        learner_dir.mkdir(parents=True, exist_ok=True)
        (learner_dir / PIECES[current]["file"]).write_text(code)
        piece["status"] = "passed"
    progress.save(prog)
    return {"results": results, "passed": all_passed, "ownership": progress.ownership(prog)}


@app.post("/api/hint")
def get_hint(code: str = Body(), after_submit: bool = Body(False)):
    """A hint for the current code. After a failed submit it targets the failing tests."""
    prog = progress.load()
    current = prog["current"]
    if not current:
        return {"hint": "Start a round first."}
    results = prog["pieces"][current]["last_results"] if after_submit else None
    return {"hint": llm.hint(current, code, results)}


PASS_SCORE = 7
MAX_HINTS = 2


@app.post("/api/explain")
def explain(explanation: str = Body(embed=True)):
    """Grade the learner's explanation. Two targeted hints on weak answers, then the full explanation.
    The score never touches their code or the ownership %."""
    prog = progress.load()
    current = prog["current"]
    piece = prog["pieces"].get(current)
    if not piece or piece["status"] != "passed":
        return {"error": "Pass the tests first, then explain your code."}
    check = piece["check"]
    if check["done"]:
        return {"error": "You've already finished the check for this piece."}
    result = llm.grade(current, explanation, piece["draft"])
    if result is None:
        return {"error": llm.BUSY}
    check["attempts"] += 1
    check["best_score"] = max(check["best_score"] or 0, result["score"])
    if result["score"] < PASS_SCORE and check["attempts"] <= MAX_HINTS:
        # Only the hint: the full feedback would hand over the explanation before they retry.
        response = {"score": result["score"], "done": False,
                    "hint": result["hint"] or "You're close. Think about what each function does with tricky inputs."}
    else:
        check["done"] = True
        response = {"score": result["score"], "feedback": result["missing"], "extra": result["extra"], "done": True}
        if result["score"] < PASS_SCORE:
            response["final_explanation"] = PIECES[current]["model_explanation"]
    progress.save(prog)
    return response


@app.post("/api/ask")
def ask(question: str = Body(embed=True)):
    prog = progress.load()
    current = prog["current"]
    if not current:
        return {"answer": "Start a round first."}
    return {"answer": llm.answer(current, question, prog["pieces"][current]["draft"] or "")}


@app.post("/api/run")
def run():
    return runner.run_store(passed=progress.passed(progress.load()))
