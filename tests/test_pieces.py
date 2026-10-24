"""Every test of a piece is listed as a passing criterion in the task, and every criterion is a real test."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from tutor.pieces import PIECES  # noqa: E402


def test_criteria_match_tests():
    for piece in PIECES.values():
        tree = ast.parse((ROOT / piece["test"]).read_text())
        tests = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
        criteria = {test for _, _, crit in piece["functions"] for test, _ in crit}
        assert criteria == tests, piece["title"]
