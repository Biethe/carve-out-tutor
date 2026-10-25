"""The tutor app: serves the pages and the JSON API on localhost:8000."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from tutor import llm, overview, progress, runner
from tutor.pieces import PIECES, assemble, function, task

PAGES = Path(__file__).parent / "pages"
PASS_SCORE = 7
MAX_HINTS = 2


@asynccontextmanager
async def lifespan(app):
    yield
    runner.stop_store()  # don't leave the store running after the tutor stops


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def always_fresh(request, call_next):
    """Browsers must check for a newer page or script every time, so a new feature never hides behind an old cached file."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
# The store's asset pictures, so the catalog can show the real project.
app.mount("/store-assets", StaticFiles(directory=Path(__file__).parent.parent / "store" / "static" / "assets"), name="store-assets")


@app.get("/")
def catalog():
    return FileResponse(PAGES / "catalog.html")


@app.get("/project")
def project():
    return FileResponse(PAGES / "project.html")


@app.get("/learn")
def learn():
    return FileResponse(PAGES / "learn.html")


@app.get("/interview")
def interview_page():
    return FileResponse(PAGES / "interview.html")


def _current(prog: dict) -> tuple[str | None, str | None, dict | None]:
    """(piece, function name, that function's progress) for the open step, or Nones."""
    piece, name = prog["current"], prog["step"]
    if not piece:
        return None, None, None
    return piece, name, prog["pieces"][piece][name]


@app.get("/api/state")
def state():
    prog = progress.load()
    piece, name, fn = _current(prog)
    result = {"current": piece, "ownership": progress.ownership(prog), "all_done": progress.all_done(prog)}
    if piece:
        names = [f["name"] for f in PIECES[piece]["functions"]]
        f = function(piece, name)
        result.update(
            round=list(PIECES).index(piece) + 1,
            total_rounds=len(PIECES),
            step=names.index(name) + 1,
            total_steps=len(names),
            task=task(piece, name),
            code=fn["draft"] if fn["draft"] is not None else f["stub"],
            status=fn["status"],
            last_results=fn["last_results"],
            check={**fn["check"], "question": f["question"]},
        )
    return result


@app.post("/api/next")
def next_step():
    """Open the next function that hasn't passed (the rest of this piece first, then the next piece).
    Ignored while the current function is still in progress."""
    prog = progress.load()
    piece, name, fn = _current(prog)
    if fn and fn["status"] != "passed":
        return state()
    for piece in PIECES:
        for f in PIECES[piece]["functions"]:
            if prog["pieces"][piece][f["name"]]["status"] != "passed":
                prog["current"], prog["step"] = piece, f["name"]
                prog["pieces"][piece][f["name"]]["status"] = "in_progress"
                progress.save(prog)
                return state()
    return state()


@app.put("/api/code")
def save_code(code: str = Body(embed=True)):
    prog = progress.load()
    _, _, fn = _current(prog)
    if fn and fn["status"] == "in_progress":
        fn["draft"] = code
        progress.save(prog)
    return {"saved": True}


@app.post("/api/submit")
async def submit(code: str = Body(embed=True)):
    """Test the learner's function inside the piece's file. On pass, it runs in the store from now on.
    A passed function can be resubmitted (a cleaner version); it only replaces the old one if it passes too."""
    prog = progress.load()
    piece, name, fn = _current(prog)
    if not fn or fn["status"] not in ("in_progress", "passed"):
        return {"error": "No open step to submit to."}
    cleaning = fn["status"] == "passed"
    results = await runner.run_tests(piece, assemble(piece, {**progress.passed_snippets(prog, piece), name: code}))
    all_passed = all(r["passed"] for r in results)
    if all_passed or not cleaning:
        fn["draft"], fn["last_results"] = code, results
    if all_passed:
        # Once a function passes it is the learner's for good: Run project uses it from now on.
        fn["status"] = "passed"
        progress.write_learner_file(prog, piece)
    progress.save(prog)
    return {"results": results, "passed": all_passed, "ownership": progress.ownership(prog),
            "all_done": progress.all_done(prog)}


@app.post("/api/hint")
async def get_hint(code: str = Body(), after_submit: bool = Body(False)):
    """A hint for the current code. After a failed submit it targets the failing tests."""
    prog = progress.load()
    piece, name, fn = _current(prog)
    if not fn:
        return {"hint": "Start learning first."}
    results = fn["last_results"] if after_submit else None
    if results:
        # Tests of other functions can fail because of this one; aim the hint at this function's own tests first.
        mine = {test for test, _ in function(piece, name)["criteria"]}
        if any(not r["passed"] for r in results if r["name"] in mine):
            results = [r for r in results if r["name"] in mine]
    return {"hint": await llm.hint(piece, name, code, results)}


@app.post("/api/clean")
async def clean():
    """Short hints for a cleaner version of the passed function, plus a cleaner version that passes the same tests."""
    prog = progress.load()
    piece, name, fn = _current(prog)
    if not fn or fn["status"] != "passed":
        return {"error": "Pass the tests first, then clean it up."}
    try:
        result = await llm.clean(piece, name, fn["draft"])
    except llm.NoKey:
        return {"error": llm.NO_KEY}
    if result is None:
        return {"error": llm.BUSY}
    if result["code"]:  # never show a "cleaner" answer that breaks the tests
        snippets = {**progress.passed_snippets(prog, piece), name: result["code"]}
        if not all(r["passed"] for r in await runner.run_tests(piece, assemble(piece, snippets))):
            result["code"] = ""
    return result


@app.get("/api/overview")
def project_overview():
    prog = progress.load()
    current = f"store/pieces/{PIECES[prog['current']]['file']}" if prog["current"] else None
    return {"tree": overview.tree(), "current": current, **overview.diagrams(current, prog["step"])}


@app.post("/api/explain")
async def explain(explanation: str = Body(embed=True)):
    """Grade the answer to this function's question. Up to two narrower follow-up questions, then the answer.
    The score never touches the learner's code or the ownership %."""
    prog = progress.load()
    piece, name, fn = _current(prog)
    if not fn or fn["status"] != "passed":
        return {"error": "Pass the tests first, then answer the question."}
    check = fn["check"]
    if check["done"]:
        return {"error": "You've already answered the question for this function."}
    try:
        result = await llm.grade(piece, name, explanation, fn["draft"], check["explanations"])
    except llm.NoKey:
        return {"error": llm.NO_KEY}
    if result is None:
        return {"error": llm.BUSY}
    check["explanations"].append(explanation)
    check["attempts"] += 1
    # Answers build on each other, so the score never goes down.
    result["score"] = check["best_score"] = max(check["best_score"] or 0, result["score"])
    if result["score"] < PASS_SCORE and check["attempts"] <= MAX_HINTS:
        # Only the follow-up question: the full feedback would hand over the answer before they retry.
        response = {"score": result["score"], "done": False,
                    "hint": result["hint"] or "What happens in your function with a tricky input?"}
    else:
        check["done"] = True
        response = {"score": result["score"], "feedback": result["missing"], "extra": result["extra"], "done": True}
        if result["score"] < PASS_SCORE:
            response["final_explanation"] = function(piece, name)["answer"]
    progress.save(prog)
    return response


@app.post("/api/ask")
async def ask(question: str = Body(), code: str = Body("")):
    prog = progress.load()
    piece, name, _ = _current(prog)
    if not piece:
        return {"answer": "Start learning first, then ask me anything about your function."}
    return {"answer": await llm.answer(piece, name, question, code)}


@app.post("/api/run")
def run():
    return runner.run_store(passed=progress.swapped(progress.load()))


@app.get("/api/settings")
def get_settings():
    """The AI provider settings, without the key itself."""
    key = llm._env("LLM_API_KEY") or llm._env("GROQ_API_KEY") or ""
    return {"base_url": llm._env("LLM_BASE_URL", llm.DEFAULTS["LLM_BASE_URL"]),
            "model": llm._env("LLM_MODEL", llm.DEFAULTS["LLM_MODEL"]), "key_end": key[-4:]}


@app.put("/api/settings")
def put_settings(base_url: str = Body(), model: str = Body(), api_key: str = Body("")):
    """Saved in this browser (or data/ locally). An empty key keeps the one already saved."""
    saved = llm.settings()
    saved.update(LLM_BASE_URL=base_url.strip(), LLM_MODEL=model.strip())
    if api_key.strip():
        saved["LLM_API_KEY"] = api_key.strip()
    progress.DATA.mkdir(parents=True, exist_ok=True)
    llm.SETTINGS.write_text(json.dumps(saved))
    return get_settings()


MAX_QUESTIONS = 7


@app.get("/api/profile")
def get_profile():
    return progress.load_profile()


@app.post("/api/interview")
async def interview(answer: str = Body("", embed=True)):
    """Saves the answer to the open question, then returns the next question or the finished profile."""
    profile = progress.load_profile()
    if profile["done"]:
        return {"done": True, "profile": profile}
    if profile["pending"] and answer.strip():
        profile["interview"].append({"q": profile["pending"], "a": answer.strip()})
    try:
        step = await llm.interview(profile["interview"], finish=len(profile["interview"]) >= MAX_QUESTIONS)
    except llm.NoKey:
        return {"error": llm.NO_KEY, "no_key": True}
    if step is None:
        return {"error": llm.BUSY}
    if step["done"]:
        profile.update({k: v for k, v in step.items()}, pending=None)
    else:
        profile["pending"] = step["question"]
    progress.save_profile(profile)
    return {"done": step["done"], "question": profile["pending"], "number": len(profile["interview"]) + 1, "profile": profile}


@app.post("/api/interview/restart")
def restart_interview():
    progress.save_profile({**progress.load_profile(), "done": False, "pending": None, "interview": []})
    return {"restarted": True}


@app.put("/api/profile")
def edit_profile(claims: list[dict] = Body(), gaps: list[str] = Body(), wants: list[str] = Body()):
    """The learner can remove claims, gaps or goals that aren't right."""
    profile = progress.load_profile()
    profile.update(claims=claims, gaps=gaps, wants=wants)
    progress.save_profile(profile)
    return profile


@app.post("/api/speak")
async def speak(text: str = Body(embed=True)):
    """The tutor's words in a natural AI voice (WAV). On an error the page falls back to the browser's own voice."""
    try:
        return Response(await llm.speech(text[:600]), media_type="audio/wav")
    except llm.NoKey:
        return JSONResponse({"error": llm.NO_KEY}, status_code=400)
    except Exception as err:
        message = str(err)
        if "terms" in message:
            message = "For the natural voice, accept Groq's terms for Orpheus once: https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
        return JSONResponse({"error": message[:300]}, status_code=502)
