"""Saves tutor progress in data/progress.json and computes the ownership percentage."""
import json
from pathlib import Path

from tutor.pieces import PIECES

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
PATH = DATA / "progress.json"


def load() -> dict:
    progress = json.loads(PATH.read_text()) if PATH.exists() else {"current": None, "pieces": {}}
    for piece in PIECES:
        progress["pieces"].setdefault(piece, {
            "status": "not_started", "draft": None, "last_results": None,
            "check": {"attempts": 0, "best_score": None, "done": False, "explanations": []},
        })
    return progress


def save(progress: dict):
    DATA.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(progress, indent=2))


def passed(progress: dict) -> list[str]:
    return [p for p, state in progress["pieces"].items() if state["status"] == "passed"]


def count_lines(code: str) -> int:
    """Non-blank lines that aren't comments."""
    return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))


def ownership(progress: dict) -> float:
    """Learner's lines ÷ all lines across the store's .py files as they'd run, as a percentage."""
    learner_files = {PIECES[p]["file"]: DATA / "learner" / PIECES[p]["file"] for p in passed(progress)}
    mine = total = 0
    for path in (ROOT / "store").rglob("*.py"):
        if path.parent.name == "pieces" and path.name in learner_files:
            lines = count_lines(learner_files[path.name].read_text())
            mine += lines
        else:
            lines = count_lines(path.read_text())
        total += lines
    return round(100 * mine / total, 1) if total else 0.0
