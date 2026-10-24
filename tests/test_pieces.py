"""The tutor's piece definitions stay in sync with the store and its tests."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from tutor.pieces import PIECES, assemble, reference_code  # noqa: E402


def test_criteria_match_tests():
    for piece in PIECES.values():
        tree = ast.parse((ROOT / piece["test"]).read_text())
        tests = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
        criteria = {test for f in piece["functions"] for test, _ in f["criteria"]}
        assert criteria == tests, piece["title"]


def test_assemble_swaps_one_function():
    for key, piece in PIECES.items():
        original = (ROOT / "store" / "pieces" / piece["file"]).read_text()
        names = [f["name"] for f in piece["functions"]]
        # Swapping in each function's own source gives back the original file.
        assert assemble(key, {n: reference_code(f"pieces/{piece['file']}", n) for n in names}) == original
        # Swapping in a stub replaces only that function.
        first = piece["functions"][0]
        swapped = assemble(key, {first["name"]: first["stub"]})
        assert "raise NotImplementedError" in swapped
        assert reference_code(f"pieces/{piece['file']}", names[1]) in swapped
