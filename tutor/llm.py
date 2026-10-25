"""The only file that talks to the AI. Groq by default; any OpenAI-compatible endpoint works via env vars."""
import json
import os
import re
from pathlib import Path

from openai import OpenAI

from tutor.pieces import PIECES, function

BUSY = "The tutor is busy, try again in a minute."


def _env(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment, or from a local .env file (never committed)."""
    if name in os.environ:
        return os.environ[name]
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name:
                return value.strip().strip("\"'")
    return default


def _chat(system: str, user: str, json_mode: bool = False) -> str:
    api_key = _env("LLM_API_KEY") or _env("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("No API key set")
    client = OpenAI(base_url=_env("LLM_BASE_URL", "https://api.groq.com/openai/v1"), api_key=api_key, timeout=30)
    reply = client.chat.completions.create(
        model=_env("LLM_MODEL", "openai/gpt-oss-120b"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        reasoning_effort="low",  # keeps replies quick and inside the free tier's token budget
        **({"response_format": {"type": "json_object"}} if json_mode else {}),
    )
    text = reply.choices[0].message.content or ""
    # House style: no em or en dashes in anything the learner reads.
    return text.replace(" — ", ", ").replace("—", ", ").replace(" – ", " - ").replace("–", "-")


def _task_text(piece: str, name: str) -> str:
    f = function(piece, name)
    calls = "\n".join(f"- {c}" for c in f["call_sites"])
    return (f"The learner is writing ONE function of the {PIECES[piece]['title']} piece ({PIECES[piece]['file']}):\n"
            f"{f['signature']}: {f['description']}\n\nWhere it's used:\n{calls}")


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


def hint(piece: str, name: str, code: str, results: list[dict] | None = None) -> str:
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
        return _strip_code(_chat(HINT_RULES, "\n\n".join(parts))) or BUSY
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


def grade(piece: str, name: str, explanation: str, code: str, earlier: list[str]) -> dict | None:
    """Score an answer together with earlier attempts: {score, missing, extra, hint}. None if the AI is unavailable."""
    f = function(piece, name)
    previous = "".join(f"\n\nTheir earlier answer {i}:\n{e}" for i, e in enumerate(earlier, 1))
    user = (f"{_task_text(piece, name)}\n\nThe question: {f['question']}\nReference answer: {f['answer']}"
            f"\n\nThe learner's code:\n{code}{previous}\n\n{'Their newest answer' if earlier else 'Their answer'}:\n{explanation}")
    for _ in range(2):  # one retry if the reply isn't valid JSON
        try:
            data = json.loads(_chat(GRADE_RULES, user, json_mode=True))
            return {
                "score": max(0, min(10, int(data["score"]))),
                "missing": str(data.get("missing") or ""),
                "extra": str(data.get("extra") or ""),
                "hint": _strip_code(str(data.get("hint") or "")),
            }
        except (ValueError, KeyError, TypeError):
            continue
        except Exception:
            return None
    return None


CLEAN_RULES = """A beginner's Python function already passes all its tests. Review it for cleanliness only:
fewer lines, simpler logic, clearer names, idiomatic Python, no wasted work. Behavior must stay exactly the same.
Reply with JSON only, with these keys:
"clean": true if it is already about as clean as it gets, else false,
"hints": 1 to 3 hints, each ONE short sentence under 15 words, pointing at one concrete improvement, no code ([] if clean),
"code": the cleaner version of the whole function, same signature, plain Python, no markdown fences ("" if clean)."""


def clean(piece: str, name: str, code: str) -> dict | None:
    """{clean, hints, code} for a passing function. None if the AI is unavailable."""
    for _ in range(2):  # one retry if the reply isn't valid JSON
        try:
            data = json.loads(_chat(CLEAN_RULES, f"{_task_text(piece, name)}\n\nTheir passing code:\n{code}", json_mode=True))
            return {
                "clean": bool(data.get("clean")),
                "hints": [_strip_code(str(h)) for h in data.get("hints") or []][:3],
                "code": re.sub(r"^```\w*\n|```\s*$", "", str(data.get("code") or "")).strip(),
            }
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        except Exception:
            return None
    return None


ANSWER_RULES = """You are a coding tutor acting as a quick, friendly reference for a beginner writing one Python function.
They may ask about a library, a method, an attribute, a concept or an error message.
Answer briefly (under 100 words) and precisely: name modules, list relevant methods or attributes and what they do,
explain concepts, and use tiny generic examples that aren't about their task.
Format: short plain sentences, or a simple list with "- " bullets. No tables, no headings.
Never write the function they are working on, or the lines that would solve it."""


def answer(piece: str, name: str, question: str, code: str) -> str:
    try:
        reply = _chat(ANSWER_RULES, f"{_task_text(piece, name)}\n\nThe learner's current code:\n{code}\n\nTheir question:\n{question}")
        return reply.strip() or BUSY
    except Exception:
        return BUSY
