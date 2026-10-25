"""The only file that talks to the AI. Groq by default; any OpenAI-compatible endpoint works.
Settings come from the environment, the learner's Settings (data/settings.json), or a local .env file."""
import asyncio
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from tutor.pieces import PIECES, function
from tutor.progress import DATA, load_profile

BUSY = "The tutor is busy, try again in a minute."
NO_KEY = "Add your AI key in Settings (the gear at the top). Groq gives free keys at console.groq.com."
DEFAULTS = {"LLM_BASE_URL": "https://api.groq.com/openai/v1", "LLM_MODEL": "openai/gpt-oss-120b"}
SETTINGS = DATA / "settings.json"


class NoKey(Exception):
    pass


def settings() -> dict:
    return json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}


def _env(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment, the learner's Settings, or a local .env file (never committed)."""
    if name in os.environ:
        return os.environ[name]
    if settings().get(name):
        return settings()[name]
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name:
                return value.strip().strip("\"'")
    return default


async def _post(url: str, headers: dict, body: dict) -> dict:
    """POST JSON and return the JSON reply. In the browser (Pyodide) this is the page's fetch."""
    if sys.platform == "emscripten":
        from pyodide.http import pyfetch
        reply = await pyfetch(url, method="POST", headers=headers, body=json.dumps(body))
        if not reply.ok:
            raise RuntimeError(f"{reply.status}: {await reply.string()}")
        return await reply.json()

    def send():
        request = urllib.request.Request(url, json.dumps(body).encode(), {**headers, "User-Agent": "carve-out-tutor"})
        try:
            with urllib.request.urlopen(request, timeout=60) as reply:
                return json.load(reply)
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"{err.code}: {err.read().decode('utf-8', 'replace')}") from None
    return await asyncio.to_thread(send)


async def _post_audio(url: str, headers: dict, body: dict) -> bytes:
    """POST JSON and return the raw reply (audio). Raises RuntimeError with the provider's message on failure."""
    if sys.platform == "emscripten":
        from pyodide.http import pyfetch
        reply = await pyfetch(url, method="POST", headers=headers, body=json.dumps(body))
        if not reply.ok:
            raise RuntimeError(await reply.string())
        return await reply.bytes()

    def send():
        request = urllib.request.Request(url, json.dumps(body).encode(), {**headers, "User-Agent": "carve-out-tutor"})
        try:
            with urllib.request.urlopen(request, timeout=30) as reply:
                return reply.read()
        except urllib.error.HTTPError as err:
            raise RuntimeError(err.read().decode("utf-8", "replace")) from None
    return await asyncio.to_thread(send)


# Chip's one voice: Groq's Orpheus, free but only about 3,600 characters a day per key. Onboarding is pre-recorded in
# it (tutor/record_intro.py); when live speech isn't available, Chip's words stay on screen instead of changing voice.
SPEECH = {"api.groq.com": ("canopylabs/orpheus-v1-english", "hannah"), "api.openai.com": ("gpt-4o-mini-tts", "coral")}


async def speech(text: str, voice: str | None = None, direction: str | None = "[cheerful]") -> bytes:
    """WAV audio of the text in a natural voice. Raises NoKey, or RuntimeError if the provider has no voice for us.
    `direction` is Orpheus' delivery note (not read out); None lets the voice speak plainly."""
    api_key = _env("LLM_API_KEY") or _env("GROQ_API_KEY")
    if not api_key:
        raise NoKey()
    base = _env("LLM_BASE_URL", DEFAULTS["LLM_BASE_URL"]).rstrip("/")
    model, default_voice = next((v for host, v in SPEECH.items() if host in base), (None, None))
    voice = voice or default_voice
    if not model:
        raise RuntimeError("Your AI provider has no natural voice here, so the browser's voice is used.")
    if "orpheus" in model and direction and not text.startswith("["):
        text = f"{direction} {text}"
    body = {"model": model, "voice": voice, "input": text, "response_format": "wav"}
    return await _post_audio(base + "/audio/speech", {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, body)


async def _chat(system: str, user: str, json_mode: bool = False) -> str:
    api_key = _env("LLM_API_KEY") or _env("GROQ_API_KEY")
    if not api_key:
        raise NoKey()
    model = _env("LLM_MODEL", DEFAULTS["LLM_MODEL"])
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"  # keeps replies quick and inside the free tier's token budget
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    url = _env("LLM_BASE_URL", DEFAULTS["LLM_BASE_URL"]).rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        reply = await _post(url, headers, body)
    except Exception as err:  # free plans limit tokens per minute: wait as long as asked (up to 20 s), once
        wait = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", str(err))
        if not ("429" in str(err) or "rate_limit" in str(err) or "Too Many" in str(err)):
            raise
        await asyncio.sleep(min(20.0, (int(wait[1] or 0) * 60 + float(wait[2]) + 0.5) if wait else 10.0))
        reply = await _post(url, headers, body)
    text = reply["choices"][0]["message"]["content"] or ""
    # House style: no em or en dashes in anything the learner reads.
    return text.replace(" — ", ", ").replace("—", ", ").replace(" – ", " - ").replace("–", "-")


def _task_text(piece: str, name: str) -> str:
    f = function(piece, name)
    calls = "\n".join(f"- {c}" for c in f["call_sites"])
    profile = load_profile()
    about = f"\n\nAbout the learner ({profile['level']}): {profile['summary']} Pitch your reply at their level." if profile["done"] else ""
    return (f"The learner is writing ONE function of the {PIECES[piece]['title']} piece ({PIECES[piece]['file']}):\n"
            f"{f['signature']}: {f['description']}\n\nWhere it's used:\n{calls}{about}")


def _strip_code(text: str) -> str:
    """Backstop: remove fenced code blocks, even an unclosed one at the end."""
    return re.sub(r"```.*?(```|$)", "", text, flags=re.S).strip()


HINT_RULES = """You are a coding tutor for a beginner who is rebuilding one function of a working Python web app.
Nudge, don't solve. Rules:
- Give 1 to 3 hints, one per line, each starting with "- ". Each hint is ONE short sentence, under 15 words.
- Straight to the point: no greeting, no praise, no restating the task, no summary at the end.
- Each hint names one concrete thing to check or try. Together they must not spell out the whole approach.
- Never write code: no code blocks, no lines of the solution, no calls with arguments, no chained calls like a.b(...).c().
- You may name a module, function or concept (for example "the hashlib module") without showing how to call it."""


async def hint(piece: str, name: str, code: str, results: list[dict] | None = None) -> str:
    """A nudge toward the goal. After a failed submit, `results` focuses it on the failing tests."""
    parts = [_task_text(piece, name), f"The learner's current code:\n{code}"]
    if results:
        failing = [f"- {r['name']}: {r['message']}" for r in results if not r["passed"]]
        passing = [r["name"] for r in results if r["passed"]]
        parts.append("They just ran the tests. Failing (focus your hint on the most important one):\n" + "\n".join(failing))
        if passing:
            parts.append("Already passing, don't talk about these: " + ", ".join(passing))
    else:
        parts.append("They asked for a hint while writing code.")
    try:
        return _strip_code(await _chat(HINT_RULES, "\n\n".join(parts))) or BUSY
    except NoKey:
        return NO_KEY
    except Exception:
        return BUSY


GRADE_RULES = """A beginner just wrote a function (its tests pass) and answered ONE narrow question about it.
Grade the answer against the reference answer. Plain words are fine; don't demand jargon.
If they answered before, judge ALL their answers together: the newest adds to what they already said,
so a point made earlier still counts, and adding detail can never lower the score.
Reply with JSON only, with these keys:
"score": integer 0-10 (7 or more means they got the main idea),
"missing": one sentence to the learner on what was missing or imprecise ("" if nothing),
"extra": one sentence of useful extra knowledge for similar work later,
"hint": if score < 7, ONE short, narrower follow-up question that points at the missing idea without answering it; otherwise ""."""


async def grade(piece: str, name: str, explanation: str, code: str, earlier: list[str]) -> dict | None:
    """Score an answer together with earlier attempts: {score, missing, extra, hint}. None if the AI is unavailable."""
    f = function(piece, name)
    previous = "".join(f"\n\nTheir earlier answer {i}:\n{e}" for i, e in enumerate(earlier, 1))
    user = (f"{_task_text(piece, name)}\n\nThe question: {f['question']}\nReference answer: {f['answer']}"
            f"\n\nThe learner's code:\n{code}{previous}\n\n{'Their newest answer' if earlier else 'Their answer'}:\n{explanation}")
    for _ in range(2):  # one retry if the reply isn't valid JSON
        try:
            data = json.loads(await _chat(GRADE_RULES, user, json_mode=True))
            return {
                "score": max(0, min(10, int(data["score"]))),
                "missing": str(data.get("missing") or ""),
                "extra": str(data.get("extra") or ""),
                "hint": _strip_code(str(data.get("hint") or "")),
            }
        except (ValueError, KeyError, TypeError):
            continue
        except NoKey:
            raise
        except Exception:
            return None
    return None


CLEAN_RULES = """A beginner's Python function already passes all its tests. Review it as production code:
- shorter: fewer lines, no wasted variables or steps, idiomatic Python;
- efficient: no needless loops, copies or repeated work;
- robust: handles odd inputs (empty, missing, wrong type) the way its callers need;
- secure: nothing an attacker could exploit (timing leaks, injection, trusting user input);
- typed: type hints on every parameter and the return value, and on local variables whose type isn't obvious,
  written with built-in types (list[int], dict[str, str], X | None), never typing.List or typing.Dict;
Keep the behavior the tests check exactly the same, and keep the exact signature from the task.
The shortest correct version wins: only guard against inputs the callers listed under "Where it's used" can really send,
and never change what happens on bad input (an error stays an error) unless that is a security fix.
Reply with JSON only, with these keys:
"clean": true if it is already about as clean as it gets, else false,
"hints": 1 to 3 points, the most important first, each ONE short sentence under 20 words that starts with its kind
("Shorter:", "Faster:", "Robust:", "Secure:" or "Typed:") and says what the cleaner version changes and why it's better, no code ([] if clean),
"code": the cleaner version of the whole function, same signature, plain Python, no markdown fences ("" if clean).
If the code is already clean, say so: "clean": true, with no hints and no code. Don't invent changes."""


async def clean(piece: str, name: str, code: str) -> dict | None:
    """{clean, hints, code} for a passing function. None if the AI is unavailable."""
    for _ in range(2):  # one retry if the reply isn't valid JSON
        try:
            data = json.loads(await _chat(CLEAN_RULES, f"{_task_text(piece, name)}\n\nTheir passing code:\n{code}", json_mode=True))
            return {
                "clean": bool(data.get("clean")),
                "hints": [_strip_code(str(h)) for h in data.get("hints") or []][:3],
                "code": re.sub(r"^```\w*\n|```\s*$", "", str(data.get("code") or "")).strip(),
            }
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        except NoKey:
            raise
        except Exception:
            return None
    return None


ANSWER_RULES = """You are a coding tutor answering a beginner's question while they write ONE Python function.
They ask so they can understand what their function should do. Answer only what they need for that. Rules:
- At most 3 short sentences, under 60 words in all. No lists of facts, no history, nothing they didn't ask.
- Everyday words, like explaining to a friend. No jargon (not "deterministic", "idempotent"): say what it means instead.
- Give one small example as "what goes in → what comes out" (for example: "hello" → 2cf24d…, "hellp" → 1a9f…).
  No code for "what is" or "why" questions. Only for "how do I use X" may you show code, and then never the call
  their function needs: show a different method or different data.
- End with one sentence linking the idea to their function: why it matters for what they're writing.
- Never write their function, the lines that would solve it, or the exact call their function needs.
Format: plain sentences. A code example goes in a ``` block."""


async def answer(piece: str, name: str, question: str, code: str) -> str:
    try:
        reply = await _chat(ANSWER_RULES, f"{_task_text(piece, name)}\n\nThe learner's current code:\n{code}\n\nTheir question:\n{question}")
        return reply.strip() or BUSY
    except NoKey:
        return NO_KEY
    except Exception:
        return BUSY


INTERVIEW_RULES = """You are Chip, a friendly coding tutor. You interview a learner to find their real level before they
rebuild parts of a working Python web app: password hashing, login checks, sessions, a shopping cart, a SQLite database.
Every question is a YES-OR-NO question, short (under 15 words), plain, read aloud. One concrete skill each.
Good: "Have you written a Python function that returns a dictionary?" Bad: "How good are you at Python?"
The first three questions each cover a DIFFERENT area, in this order: 1) Python itself, 2) web apps (forms, logins,
sessions), 3) databases (SQL) or security (password hashing). Earlier answers only set the difficulty: after a yes, ask a
harder question in the next area; after a no, an easier one. Never spend a question on trivia like printing text.
Later questions (if any) go deeper where the gaps are: testing, specific skills, or what they want to focus on.
Before each new question, react to their last answer in "feedback": a few warm words (under 8), e.g. "Nice." or
"Good to know." Never judge. For the very first question, "feedback" is "".
Reply with JSON only. While asking: {"done": false, "feedback": "...", "question": "..."}
When told to finish: {"done": true, "closing": "a short, upbeat line (under 12 words), e.g. 'Great, that's all I need. Let's build.'",
"level": "beginner" or "intermediate" or "advanced", "summary": "one sentence describing them, for a tutor",
"claims": [{"skill": "short skill name", "said": "yes to: <the question, shortened>"}] (only what they said yes to),
"gaps": ["short skill name"] (what they said no to), "wants": ["what they'd like to focus on, if they said"]}"""


async def interview(history: list[dict], finish: bool) -> dict | None:
    """The next interview question, or the finished profile. None if the AI is unavailable; NoKey if there's no key."""
    talk = "\n".join(f"Tutor: {h['q']}\nLearner: {h['a']}" for h in history)
    user = (f"The interview so far:\n{talk}\n\n" if history else "Start: ask the first question. Don't greet them again.\n\n")
    if finish:
        user += "You have enough now. Finish: reply with the done JSON."
    for _ in range(2):  # one retry if the reply isn't valid JSON
        try:
            data = json.loads(await _chat(INTERVIEW_RULES, user, json_mode=True))
            if data.get("done"):
                return {"done": True, "closing": str(data.get("closing") or ""), "level": str(data.get("level") or "beginner"), "summary": str(data.get("summary") or ""),
                        "claims": [{"skill": str(c.get("skill", "")), "said": str(c.get("said", "")), "status": "claimed"}
                                   for c in data.get("claims") or [] if isinstance(c, dict)],
                        "gaps": [str(g) for g in data.get("gaps") or []],
                        "wants": [str(w) for w in data.get("wants") or []]}
            if data.get("question"):
                return {"done": False, "question": _strip_code(str(data["question"])), "feedback": str(data.get("feedback") or "")}
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        except NoKey:
            raise
        except Exception:
            return None
    return None


CARD_RULES = """A learner will rewrite ONE function of a small, working Python web app (FastAPI, Jinja2 templates, SQLite)
from an empty stub. Write their task card and the pytest tests their version must pass.
Card, in plain words for a beginner, never giving away the code:
- "description": 2-3 sentences: what the function receives, what it must do and give back. No implementation steps.
- "breaks": one sentence: what goes wrong in the app if this function is wrong.
- "question": ONE narrow question about why it's written this way (asked after they pass). "answer": 2-3 sentences.
- "criteria": one {"test": "<test function name>", "text": "..."} per test. The text says what the FUNCTION must do,
  like "Returns every user with their password hash" or "A wrong password shows the login page again", never how
  the test does it (not "Calls db.init(), then...").
Tests ("tests": a complete pytest file as a string), 2 to 4 small test functions:
- The store's folder is already on sys.path: just import modules by name (import db, import app, from cart import add_item).
  Never change sys.path, os.environ or STORE_DB, and never open the database file yourself: use the db module's functions.
- Every test starts with an empty database. Call db.init() first if the database is needed;
  init() creates the tables and the demo user "learner" with password "carve123" and 8 assets.
- No server, no network, no TestClient, no async. Call the function directly.
  A route gets a fake request: types.SimpleNamespace(session={}) (put keys in session as needed).
  Check what it returns: .status_code, .headers["location"], .template.name, .context["..."], or the session dict.
- Test the behaviour the app relies on (see "Where it's used"), not private details.
- They must PASS on the original function and FAIL if the function just raises NotImplementedError.
  Never write a test about the stub itself (no test that expects NotImplementedError).
Reply in exactly this format, nothing else:
CARD:
{"description": "...", "breaks": "...", "question": "...", "answer": "...", "criteria": [...]}
TESTS:
```python
<the complete pytest file>
```"""


async def card(piece: str, name: str, context: dict, problem: str = "") -> dict | None:
    """A card and tests for one function. None if the AI is unavailable or keeps replying badly."""
    user = (f"The file {context['file']}:\n{context['source']}\n\nThe function to rewrite:\n{context['function']}\n\n"
            "Where it's used:\n" + "\n".join(f"- {c}" for c in context["call_sites"])
            + (f"\n\nThe code that calls it:\n{context['callers']}" if context["callers"] else ""))
    if problem:
        user += f"\n\nYour previous tests had a problem. Fix it:\n{problem}"
    for _ in range(3):
        try:
            # Not JSON mode: escaping a whole test file inside JSON often fails. The card is JSON, the tests a code block.
            reply = await _chat(CARD_RULES, user)
            data = json.loads(reply[reply.index("{"):reply.index("TESTS:")].strip().rstrip("`").strip())
            tests = re.search(r"```(?:python)?\n(.*?)```", reply, re.S)[1].strip() + "\n"
            return {"description": str(data["description"]), "breaks": str(data.get("breaks") or ""),
                    "question": str(data["question"]), "answer": str(data.get("answer") or ""), "tests": tests,
                    "criteria": [c for c in data.get("criteria") or [] if isinstance(c, dict) and "test" in c and "text" in c]}
        except (ValueError, KeyError, TypeError, IndexError):
            continue
        except NoKey:
            raise
        except Exception as err:
            if "429" in str(err) or "rate_limit" in str(err):
                await asyncio.sleep(30)  # cards are written in the background: waiting out the minute is fine
                continue
            return None
    return None


PLAN_RULES = """You plan which functions of a small Python web app a learner rewrites, from their profile.
Mark "write" for what's worth learning for them: their gaps and goals first, then the key spots of the app
(login, password hashing, sessions, the cart, the database). Mark "keep" for plain glue or things they clearly know.
Pick 1 or 2 functions that test a skill they CLAIMED as "spot_checks", marked "write" too, to check the claim.
Order the "write" ones from most useful to least. Aim for about a third of the functions for a beginner,
half for an intermediate learner, and most for an advanced one.
Reply with JSON only: {"order": ["piece.function", ...] (the write ones, in order),
"keep": ["piece.function", ...], "reasons": {"piece.function": "why, in under 10 words"},
"spot_checks": [{"function": "piece.function", "claim": "<the claimed skill, as written in the profile>"}]}"""


async def plan(profile: dict, functions: list[dict]) -> dict | None:
    """A suggested plan: {order, keep, reasons, spot_checks}. None if the AI is unavailable."""
    listing = "\n".join(f"- {f['key']}: {f['signature']}  ({f['file']})" for f in functions)
    who = (f"Level: {profile['level']}. {profile['summary']}\nClaims: " + "; ".join(c["skill"] for c in profile["claims"])
           + "\nNew to them: " + "; ".join(profile.get("gaps") or []) + "\nGoals: " + "; ".join(profile["wants"]))
    for _ in range(2):
        try:
            data = json.loads(await _chat(PLAN_RULES, f"The learner:\n{who}\n\nThe functions:\n{listing}", json_mode=True))
            keys = {f["key"] for f in functions}
            return {"order": [k for k in data["order"] if k in keys], "reasons": {k: str(v) for k, v in (data.get("reasons") or {}).items() if k in keys},
                    "spot_checks": [s for s in data.get("spot_checks") or [] if isinstance(s, dict) and s.get("function") in keys]}
        except (ValueError, KeyError, TypeError):
            continue
        except NoKey:
            raise
        except Exception:
            return None
    return None
