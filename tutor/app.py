"""The tutor app: serves the pages and the JSON API on localhost:8000."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import inspect
import shutil

from tutor import cards, llm, onboarding, overview, pieces, progress, projects, runner, safety
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
    builtin = pieces.STORE == pieces.BUILTIN
    result = {"current": piece, "ownership": progress.ownership(prog), "all_done": progress.all_done(prog),
              "project": "Polyvault" if builtin else projects.active(), "builtin": builtin,
              "runs": projects.kind(pieces.STORE)["kind"] != "tests"}
    if piece:
        plan = progress.plan(prog)
        f = function(piece, name)
        result.update(
            step=plan.index((piece, name)) + 1 if (piece, name) in plan else 1,
            total_steps=len(plan),
            task=task(piece, name),
            code=fn["draft"] if fn["draft"] is not None else f["stub"],
            status=fn["status"],
            last_results=fn["last_results"],
            check={**fn["check"], "question": f["question"]},
        )
    return result


@app.post("/api/next")
async def next_step():
    """Open the next function in the learner's plan that hasn't passed. Ignored while the current one is in progress.
    A function without a hand-written card gets its card and tests written first (tutor/cards.py); one that can't
    get reliable tests is moved to "keep the original", with the reason."""
    prog = progress.load()
    piece, name, fn = _current(prog)
    if fn and fn["status"] != "passed":
        return state()
    for piece, name in progress.plan(prog):
        f = prog["pieces"][piece][name]
        if f["status"] == "passed":
            continue
        if function(piece, name).get("auto"):
            try:
                problem = await cards.prepare(piece, name)
            except llm.NoKey:
                return {**state(), "error": llm.NO_KEY}
            if problem == llm.BUSY:
                return {**state(), "error": "Chip is busy preparing your next function. Try again in a minute."}
            prog = progress.load()  # re-read after the wait
            f = prog["pieces"][piece][name]
            if problem:
                plan = _plan(prog)
                plan["marks"][f"{piece}.{name}"] = "keep"
                plan["reasons"][f"{piece}.{name}"] = problem
                prog["plan"] = plan
                continue
        prog["current"], prog["step"] = piece, name
        f["status"] = "in_progress"
        progress.save(prog)
        return state()
    progress.save(prog)
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
    results = await runner.run_tests(piece, name, assemble(piece, {**progress.passed_snippets(prog, piece), name: code}))
    prog = progress.load()  # re-read after the wait: anything saved meanwhile (a draft, a plan) must not be lost
    fn = prog["pieces"][piece][name]
    all_passed = all(r["passed"] for r in results)
    if all_passed or not cleaning:
        fn["draft"], fn["last_results"] = code, results
    shown = None
    if all_passed:
        # Once a function passes it is the learner's for good: Run project uses it from now on.
        fn["status"] = "passed"
        progress.write_learner_file(prog, piece)
        shown = _spot_check_passed(prog, piece, name)
    progress.save(prog)
    return {"results": results, "passed": all_passed, "ownership": progress.ownership(prog),
            "all_done": progress.all_done(prog), "shown_claim": shown}


def _spot_check_passed(prog: dict, piece: str, name: str) -> str | None:
    """If this function was a spot check for a claimed skill, the claim is now shown. Returns the skill."""
    claim = _plan(prog)["spots"].get(f"{piece}.{name}")
    if not claim:
        return None
    profile = progress.load_profile()
    for c in profile["claims"]:
        if c["skill"].lower() == claim.lower() or claim.lower() in c["skill"].lower():
            c["status"] = "shown"
    progress.save_profile(profile)
    return claim


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
        if not all(r["passed"] for r in await runner.run_tests(piece, name, assemble(piece, snippets))):
            result["code"] = ""
    return result


@app.get("/api/overview")
def project_overview():
    prog = progress.load()
    current = f"{pieces.STORE.name}/{PIECES[prog['current']]['file']}" if prog["current"] else None
    return {"tree": overview.tree(), "root": pieces.STORE.name, "current": current, **overview.diagrams(current, prog["step"])}


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
    prog = progress.load()  # re-read after the wait
    check = prog["pieces"][piece][name]["check"]
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
async def run():
    prog = progress.load()
    passed = progress.swapped(prog)
    for piece in passed:  # rewritten each time, so the files always match the latest passed code
        progress.write_learner_file(prog, piece)
    result = runner.run_store(passed=passed)
    return await result if inspect.isawaitable(result) else result  # in the browser it installs packages first


@app.get("/api/settings")
def get_settings():
    """The AI provider settings, without the key itself."""
    key = llm._env("LLM_API_KEY") or llm._env("GROQ_API_KEY") or ""
    try:
        demo = llm.provider()[3]
    except llm.NoKey:
        demo = False
    return {"base_url": llm._env("LLM_BASE_URL", llm.DEFAULTS["LLM_BASE_URL"]),
            "model": llm._env("LLM_MODEL", llm.DEFAULTS["LLM_MODEL"]), "key_end": key[-4:], "demo": demo}


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


ONBOARDING_QUESTIONS = 3  # first launch: three quick yes/no questions, then straight to work
MORE_QUESTIONS = 4        # each "Improve my profile" adds up to this many


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
        step = await llm.interview(profile["interview"], finish=len(profile["interview"]) >= profile.get("limit", ONBOARDING_QUESTIONS))
    except llm.NoKey:
        return {"error": llm.NO_KEY, "no_key": True}
    if step is None:
        return {"error": llm.BUSY}
    if step["done"]:
        profile.update({k: v for k, v in step.items() if k != "closing"}, pending=None)
    else:
        profile["pending"] = step["question"]
    progress.save_profile(profile)
    return {"done": step["done"], "question": profile["pending"], "feedback": step.get("feedback", ""),
            "closing": step.get("closing", ""), "number": len(profile["interview"]) + 1,
            "of": profile.get("limit", ONBOARDING_QUESTIONS), "profile": profile}


@app.get("/api/onboarding")
def onboarding_tree():
    """The three yes/no questions as a tree, and which lines already have a recorded clip."""
    voice = Path(__file__).parent / "static" / "voice"
    return {**onboarding.tree(), "recorded": [i for i in onboarding.LINES if (voice / f"{i}.wav").exists()]}


@app.post("/api/onboarding")
def finish_onboarding(answers: list[tuple[str, bool]] = Body(embed=True)):
    """Builds the profile straight from the answers: no AI, no key."""
    if [q for q, _ in answers][:1] != ["python"] or not all(q in onboarding.QUESTIONS for q, _ in answers):
        return {"error": "Those answers don't match the questions."}
    profile = {**onboarding.profile(answers), "limit": len(answers)}
    progress.save_profile(profile)
    return profile


@app.post("/api/interview/restart")
def restart_interview():
    progress.save_profile({**progress.load_profile(), "done": False, "pending": None, "interview": [], "limit": ONBOARDING_QUESTIONS})
    return {"restarted": True}


@app.post("/api/interview/more")
def more_questions():
    """Improve the profile: a few more questions, building on the earlier answers (Chip sees them all)."""
    profile = progress.load_profile()
    progress.save_profile({**profile, "done": False, "pending": None, "limit": len(profile["interview"]) + MORE_QUESTIONS})
    return {"more": True}


@app.put("/api/profile")
def edit_profile(claims: list[dict] = Body(), gaps: list[str] = Body(), wants: list[str] = Body()):
    """The learner can remove claims, gaps or goals that aren't right."""
    profile = progress.load_profile()
    profile.update(claims=claims, gaps=gaps, wants=wants)
    progress.save_profile(profile)
    return profile


@app.post("/api/speak")
async def speak(text: str = Body(embed=True)):
    """Chip's words in Groq's Orpheus voice (WAV). On an error the page shows the words instead, never another voice."""
    try:
        return Response(await llm.speech(text[:480]), media_type="audio/wav")
    except llm.NoKey:
        return JSONResponse({"error": llm.NO_KEY}, status_code=400)
    except Exception as err:
        message = str(err)
        if "rate_limit" in message:  # per minute: try again soon. Per day: done for today.
            return JSONResponse({"error": "busy", "busy": True, "today": "per day" in message}, status_code=429)
        if "terms" in message:
            message = "For Chip's best voice, accept Groq's terms for Orpheus once: https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
        return JSONResponse({"error": message[:300]}, status_code=502)


# ---- The learner's plan: which functions they write, which keep the original ---------------------
def _plan(prog: dict) -> dict:
    """The saved plan, or the default: the six hand-made functions, in round order."""
    if prog.get("plan"):
        return prog["plan"]
    keys = [f"{piece}.{name}" for piece, name in progress.plan(prog)]
    return {"order": keys, "marks": dict.fromkeys(keys, "write"), "reasons": {}, "spots": {}}


def _functions() -> list[dict]:
    return [{"key": f"{piece}.{f['name']}", "piece": piece, "name": f["name"], "file": p["file"], "signature": f["signature"]}
            for piece, p in PIECES.items() for f in p["functions"]]


@app.get("/api/plan")
def get_plan():
    prog = progress.load()
    plan = _plan(prog)
    rank = {key: i for i, key in enumerate(plan["order"])}
    rows = [{**f, "mark": plan["marks"].get(f["key"], "keep"), "reason": plan["reasons"].get(f["key"], ""),
             "spot": plan["spots"].get(f["key"]), "status": prog["pieces"][f["piece"]][f["name"]]["status"],
             "rank": rank.get(f["key"])} for f in _functions()]
    return {"functions": rows, "suggested": bool(prog.get("plan")), "ownership": progress.ownership(prog),
            "profile": progress.load_profile()["done"]}


@app.post("/api/plan/suggest")
async def suggest_plan():
    """Chip's plan from the learner's profile: what to write (most useful first), spot checks for their claims."""
    prog = progress.load()
    profile = progress.load_profile()
    if not profile["done"]:
        return {"error": "Do the interview first, so Chip knows what to suggest."}
    try:
        suggestion = await llm.plan(profile, _functions())
    except llm.NoKey:
        return {"error": llm.NO_KEY}
    if not suggestion or not suggestion["order"]:
        return {"error": llm.BUSY}
    prog = progress.load()  # re-read after the wait: the learner may have opened or saved something meanwhile
    passed = [f"{piece}.{name}" for piece, fns in prog["pieces"].items() for name, f in fns.items() if f["status"] == "passed"]
    order = overview.roadmap(list(dict.fromkeys(passed + suggestion["order"])))  # what they've written stays theirs
    prog["plan"] = {"order": order, "marks": {f["key"]: "write" if f["key"] in order else "keep" for f in _functions()},
                    "reasons": suggestion["reasons"], "spots": {s["function"]: s["claim"] for s in suggestion["spot_checks"]}}
    progress.save(prog)
    return get_plan()


@app.put("/api/plan")
def edit_plan(marks: dict[str, str] = Body(embed=True)):
    """Mark functions "write" or "keep". The order is Chip's roadmap: roots first, then what builds on them."""
    prog = progress.load()
    plan = _plan(prog)
    for key, mark in marks.items():
        if mark in ("write", "keep"):
            plan["marks"][key] = mark
    plan["order"] = overview.roadmap([key for key, mark in plan["marks"].items() if mark == "write"])
    prog["plan"] = plan
    progress.save(prog)
    return get_plan()


# ---- Projects: Polyvault, or one the learner uploaded -----------------------------------------
projects.activate(projects.active()) and projects.activate("store")  # the last one opened (or Polyvault)


@app.get("/api/project")
def project_info():
    root = pieces.STORE
    readme = next((p for p in root.glob("README*") if p.is_file()), None)
    intro = next((block.strip() for block in (readme.read_text(errors="replace").split("\n\n") if readme else [])
                  if block.strip() and not block.lstrip().startswith(("#", "!", "[", "<", "```"))), "")
    return {"name": projects.active(), "builtin": root == pieces.BUILTIN, "kind": projects.kind(root)["kind"],
            "functions": sum(len(p["functions"]) for p in PIECES.values()), "files": len(PIECES), "intro": intro[:400],
            "safety": None if root == pieces.BUILTIN else projects.report(root.name)}


@app.get("/api/projects")
def list_projects():
    return {"projects": projects.listing(), "active": projects.active()}


@app.post("/api/projects")
async def upload_project(file: UploadFile = File(...)):
    """Unpack a zip, then check it for harmful code before anything else can happen with it."""
    name, problem = projects.unpack(file.filename or "project.zip", await file.read())
    if problem:
        return {"error": problem}
    result = await safety.check(name, projects.UPLOADS / name)
    return {"name": name, "kind": projects.kind(projects.UPLOADS / name)["kind"], **result}


@app.post("/api/projects/{name}/open")
def open_project(name: str):
    problem = projects.activate(name)
    return {"error": problem} if problem else project_info()


@app.delete("/api/projects/{name}")
def delete_project(name: str):
    if name == "store":
        return {"error": "Polyvault stays."}
    shutil.rmtree(projects.UPLOADS / name, ignore_errors=True)
    shutil.rmtree(progress.DATA / "work" / name, ignore_errors=True)
    if projects.active() == name:
        projects.activate("store")
    return list_projects()


@app.get("/api/download")
def download_project():
    name, data = projects.download()
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.post("/api/open")
async def open_function(key: str = Body(embed=True)):
    """Open any function, in any order: the roadmap is only a suggestion. A half-written one keeps its draft."""
    prog = progress.load()
    piece, name = key.rsplit(".", 1)
    if piece not in PIECES or name not in prog["pieces"][piece]:
        return {"error": "That function isn't in this project."}
    if function(piece, name).get("auto"):
        try:
            problem = await cards.prepare(piece, name)
        except llm.NoKey:
            return {"error": llm.NO_KEY}
        if problem:
            return {"error": problem}
    prog = progress.load()  # re-read after the wait
    plan = _plan(prog)
    plan["marks"][key] = "write"
    plan["order"] = overview.roadmap([k for k, m in plan["marks"].items() if m == "write"])
    prog["plan"] = plan
    prog["current"], prog["step"] = piece, name
    if prog["pieces"][piece][name]["status"] != "passed":
        prog["pieces"][piece][name]["status"] = "in_progress"
    progress.save(prog)
    return state()
