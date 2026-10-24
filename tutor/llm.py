"""The only file that talks to the AI. Groq by default; any OpenAI-compatible endpoint works via env vars."""
import json
import os
import re
from pathlib import Path

from openai import OpenAI

from tutor.pieces import PIECES

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
    return reply.choices[0].message.content or ""


def _task_text(piece: str) -> str:
    p = PIECES[piece]
    functions = "\n".join(f"- {sig}: {desc}" for sig, desc in p["functions"])
    calls = "\n".join(f"- {c}" for c in p["call_sites"])
    return f"Piece: {p['title']} ({p['file']})\n{p['summary']}\n\nFunctions to write:\n{functions}\n\nWhere it's used:\n{calls}"


def _strip_code(text: str) -> str:
    """Backstop: remove fenced code blocks, even an unclosed one at the end."""
    return re.sub(r"```.*?(```|$)", "", text, flags=re.S).strip()


HINT_RULES = """You are a patient coding tutor for a beginner who is rebuilding one piece of a working Python web app.
Your job is to nudge, not to solve. Rules:
- Talk about ONE function only: the first one that is missing or broken. Ignore the others.
- Give only the NEXT small step, never the whole approach. 2-3 sentences. Ending with a guiding question is good.
- Never write code: no code blocks, no lines of the solution, no calls with arguments, no chained calls like a.b(...).c().
- You may name at most one module, function or concept (for example "the hashlib module") without showing how to call it.
- Be warm and plain. Don't repeat the task back."""


def hint(piece: str, code: str, results: list[dict] | None = None) -> str:
    """A nudge toward the goal. After a failed submit, `results` focuses it on the failing tests."""
    parts = [_task_text(piece), f"The learner's current code:\n{code}"]
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


GRADE_RULES = """You grade a beginner's explanation of code they just wrote (their tests already pass).
Compare it with the reference explanation. Plain words are fine; don't demand jargon.
Reply with JSON only, with these keys:
"score": integer 0-10 (7 or more means they clearly understand the main ideas),
"missing": 1-2 sentences to the learner on what was missing or imprecise ("" if nothing),
"extra": 1-2 sentences of useful extra knowledge that helps with similar work later,
"hint": if score < 7, one sentence like "You're missing something about X. Think about it." that names the topic without giving the answer; otherwise ""."""


def grade(piece: str, explanation: str, code: str) -> dict | None:
    """Score an explanation: {score, missing, extra, hint}. None if the AI is unavailable."""
    user = (f"{_task_text(piece)}\n\nReference explanation:\n{PIECES[piece]['model_explanation']}"
            f"\n\nThe learner's code:\n{code}\n\nThe learner's explanation:\n{explanation}")
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


ANSWER_RULES = """You are a patient coding tutor. The learner rebuilt one piece of a working Python web app and has a question.
Answer clearly and briefly (under 120 words), in plain words, using their code and the app as context.
You may explain concepts and show tiny generic examples, but never write code for the piece's own functions."""


def answer(piece: str, question: str, code: str) -> str:
    try:
        reply = _chat(ANSWER_RULES, f"{_task_text(piece)}\n\nThe learner's code:\n{code}\n\nTheir question:\n{question}")
        return reply.strip() or BUSY
    except Exception:
        return BUSY
