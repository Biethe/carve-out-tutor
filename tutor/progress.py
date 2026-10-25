"""Saves tutor progress in data/progress.json and computes the ownership percentage."""
import json
import os
from pathlib import Path

from tutor import pieces
from tutor.pieces import HAND, PIECES, _function_spans, assemble

ROOT = Path(__file__).parent.parent
DATA = Path(os.environ.get("TUTOR_DATA", ROOT / "data"))  # override to keep test runs out of your real progress


def work() -> Path:
    """Where the active project's progress, cards and the learner's code live. Polyvault's stay in data/ itself."""
    return DATA if pieces.STORE == pieces.BUILTIN else DATA / "work" / pieces.STORE.name


def _new_function() -> dict:
    return {"status": "not_started", "draft": None, "last_results": None,
            "check": {"attempts": 0, "best_score": None, "done": False, "explanations": []}}


def load() -> dict:
    path = work() / "progress.json"
    progress = json.loads(path.read_text()) if path.exists() else {}
    if "step" not in progress:  # first start, or a file from before functions were carved one at a time
        progress = {"current": None, "step": None, "pieces": {}}
    for piece, p in PIECES.items():
        functions = progress["pieces"].setdefault(piece, {})
        for f in p["functions"]:
            functions.setdefault(f["name"], _new_function())
    return progress


def save(progress: dict):
    work().mkdir(parents=True, exist_ok=True)
    (work() / "progress.json").write_text(json.dumps(progress, indent=2))


def passed_snippets(progress: dict, piece: str) -> dict[str, str]:
    """The learner's code for each function of a piece that has passed."""
    return {name: f["draft"] for name, f in progress["pieces"][piece].items() if f["status"] == "passed"}


def swapped(progress: dict) -> list[str]:
    """Pieces with at least one of the learner's functions running in them."""
    return [piece for piece in PIECES if passed_snippets(progress, piece)]


def plan(progress: dict) -> list[tuple[str, str]]:
    """The functions the learner will write, in order: their saved plan, or else the default (Polyvault: the six
    hand-made rounds; an uploaded project: everything)."""
    if progress.get("plan"):
        return [tuple(key.rsplit(".", 1)) for key in progress["plan"]["order"] if progress["plan"]["marks"].get(key) == "write"]
    from tutor import overview
    builtin = pieces.STORE == pieces.BUILTIN  # an uploaded project starts with every function to write
    keys = [f"{piece}.{f['name']}" for piece in PIECES if piece in HAND or not builtin for f in PIECES[piece]["functions"]]
    return [tuple(key.rsplit(".", 1)) for key in overview.roadmap(keys)]


def all_done(progress: dict) -> bool:
    return all(progress["pieces"][piece][name]["status"] == "passed" for piece, name in plan(progress))


def write_learner_file(progress: dict, piece: str):
    """data/learner/<file>: the piece with every passed function swapped in. Run project uses it."""
    path = work() / "learner" / PIECES[piece]["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(assemble(piece, passed_snippets(progress, piece)))


def count_lines(code: str) -> int:
    """Non-blank lines that aren't comments."""
    return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))


def ownership(progress: dict) -> float:
    """The learner's share of the project's functions, in lines, as they'd run: writing every one is 100%.
    (Imports and setup lines between functions aren't counted: there's nothing to carve there.)"""
    mine = total = 0
    for piece, p in PIECES.items():
        source = (pieces.STORE / p["file"]).read_text()
        lines = source.splitlines()
        for name, (first, last) in _function_spans(source, decorators=False).items():
            f = progress["pieces"][piece].get(name)
            if f and f["status"] == "passed":
                mine += count_lines(f["draft"])
                total += count_lines(f["draft"])
            else:
                total += count_lines("\n".join(lines[first - 1:last]))
    return round(100 * mine / total, 1) if total else 0.0


# ---- The learner's profile, from the first-launch interview -----------------------
PROFILE = DATA / "profile.json"


def load_profile() -> dict:
    """What the learner said about themselves. Claims are "claimed" until a spot check shows them."""
    if PROFILE.exists():
        return json.loads(PROFILE.read_text())
    return {"done": False, "pending": None, "interview": [], "level": None, "summary": "", "claims": [], "gaps": [], "wants": []}


def save_profile(profile: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(json.dumps(profile, indent=2))
