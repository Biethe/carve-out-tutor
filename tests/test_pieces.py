"""The tutor's piece definitions stay in sync with the store and its tests."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from tutor.pieces import HAND, PIECES, _function_spans, assemble  # noqa: E402


def test_criteria_match_tests():
    for piece in HAND.values():
        tree = ast.parse((ROOT / piece["test"]).read_text())
        tests = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
        criteria = {test for f in piece["functions"] for test, _ in f["criteria"]}
        assert criteria == tests, piece["title"]


def test_every_function_is_carvable():
    found = {(key, f["name"]) for key, p in PIECES.items() for f in p["functions"]}
    assert ("db", "get_users") in found and ("app", "login") in found and ("auth", "check_login") in found


def test_assemble_swaps_one_function():
    for key, piece in PIECES.items():
        original = (ROOT / "store" / piece["file"]).read_text()
        lines = original.splitlines()
        own = {n: "\n".join(lines[a - 1:b]) for n, (a, b) in _function_spans(original, decorators=False).items()}
        # Swapping in each function's own source (from its `def`; decorators stay put) gives back the original file.
        assert assemble(key, own) == original, key
        # Swapping in a stub replaces only that function.
        first, second = piece["functions"][:2]
        swapped = assemble(key, {first["name"]: first["stub"]})
        assert "raise NotImplementedError" in swapped and own[second["name"]] in swapped, key
