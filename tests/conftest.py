# Lets the tests import the store's modules (`db`, `app`) and pieces (`auth`, `cart`) directly.
# The tutor's runner points STORE_DIR at a copy of the store with the learner's file swapped in,
# and STORE_DB at a database file of its own.
import os
import sys
from pathlib import Path

import pytest

STORE = Path(os.environ.get("STORE_DIR", Path(__file__).parent.parent / "store"))
sys.path[:0] = [str(STORE), str(STORE / "pieces")]


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts with an empty database (tests call db.init() to create the tables and demo data)."""
    path = os.environ.get("STORE_DB")
    if path and os.path.exists(path):
        os.remove(path)
    yield
