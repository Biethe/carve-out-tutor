# Lets the tests import `auth` and `cart` directly. The path is appended, so a learner's
# file placed earlier on PYTHONPATH by the tutor's test runner is found first.
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "store" / "pieces"))
