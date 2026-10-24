"""Saves tutor progress in data/progress.json and computes the ownership percentage."""
import json
import os
from pathlib import Path

from tutor.pieces import PIECES, assemble

ROOT = Path(__file__).parent.parent
DATA = Path(os.environ.get("TUTOR_DATA", ROOT / "data"))  # override to keep test runs out of your real progress
PATH = DATA / "progress.json"


def _new_function() -> dict:
    return {"status": "not_started", "draft": None, "last_results": None,
            "check": {"attempts": 0, "best_score": None, "done": False, "explanations": []}}


def load() -> dict:
    progress = json.loads(PATH.read_text()) if PATH.exists() else {}
    if "step" not in progress:  # first start, or a file from before functions were carved one at a time
        progress = {"current": None, "step": None, "pieces": {}}
    for piece, p in PIECES.items():
        functions = progress["pieces"].setdefault(piece, {})
        for f in p["functions"]:
            functions.setdefault(f["name"], _new_function())
    return progress


def save(progress: dict):
    DATA.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(progress, indent=2))


def passed_snippets(progress: dict, piece: str) -> dict[str, str]:
    """The learner's code for each function of a piece that has passed."""
    return {name: f["draft"] for name, f in progress["pieces"][piece].items() if f["status"] == "passed"}


def swapped(progress: dict) -> list[str]:
    """Pieces with at least one of the learner's functions running in them."""
    return [piece for piece in PIECES if passed_snippets(progress, piece)]


def all_done(progress: dict) -> bool:
    return all(f["status"] == "passed" for functions in progress["pieces"].values() for f in functions.values())


def write_learner_file(progress: dict, piece: str):
    """data/learner/<file>: the piece with every passed function swapped in. Run project uses it."""
    learner_dir = DATA / "learner"
    learner_dir.mkdir(parents=True, exist_ok=True)
    (learner_dir / PIECES[piece]["file"]).write_text(assemble(piece, passed_snippets(progress, piece)))


def count_lines(code: str) -> int:
    """Non-blank lines that aren't comments."""
    return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))


def ownership(progress: dict) -> float:
    """Learner's lines ÷ all lines across the store's .py files as they'd run, as a percentage."""
    files = {PIECES[p]["file"]: p for p in PIECES}
    mine = total = 0
    for path in (ROOT / "store").rglob("*.py"):
        piece = files.get(path.name) if path.parent.name == "pieces" else None
        snippets = passed_snippets(progress, piece) if piece else {}
        if snippets:
            mine += sum(count_lines(code) for code in snippets.values())
            total += count_lines(assemble(piece, snippets))
        else:
            total += count_lines(path.read_text())
    return round(100 * mine / total, 1) if total else 0.0
