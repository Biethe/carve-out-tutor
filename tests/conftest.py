# Lets the tests import the store's modules (`db`, `app`) and pieces (`auth`, `cart`) directly.
# The tutor's runner points STORE_DIR at a copy of the store with the learner's file swapped in,
# and STORE_DB at a database file of its own.
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

STORE = Path(os.environ.get("STORE_DIR", Path(__file__).parent.parent / "store"))
sys.path[:0] = [str(STORE), str(STORE / "pieces")]


def _sample(col: str, i: int) -> str:
    kind = col.upper()
    if any(word in kind for word in ("INT", "REAL", "NUM", "FLOAT", "DOUBLE", "DEC")):
        return str(20 + i)
    if any(word in kind for word in ("DATE", "TIME", "TEXT", "CHAR", "CLOB")):
        return f"'2018-01-10 12:0{i}:00'"
    return "NULL"


def _project_databases():
    """Create sqlite files the project opens, with the tables its scripts define.

    Some apps (a sensor logger, for example) connect and query at import time, but the
    database file is built on the original machine and is not in the repo. Without it,
    every test dies before it can call the function.
    """
    if not STORE.is_dir():
        return
    creates, connects = [], []
    for path in STORE.rglob("*.py"):
        if {"node_modules", ".git", "__pycache__"} & set(path.parts):
            continue
        text = path.read_text(errors="replace")
        creates += re.findall(r"CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)\s*\((.*?)\)", text, re.I | re.S)
        connects += [(path.parent, rel) for rel in re.findall(r"""\.connect\(\s*['\"]([^'\"]+)['\"]\s*\)""", text)
                     if rel != ":memory:"]
    if not connects:
        return
    statements = [f"CREATE TABLE IF NOT EXISTS {name} ({cols})" for name, cols in creates]
    bases = [Path.cwd(), STORE, STORE.parent]
    seen = set()
    for folder, rel in connects:
        for base in [folder, *bases]:
            dest = (base / rel).resolve()
            if dest in seen:
                continue
            seen.add(dest)
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                db = sqlite3.connect(dest)
                for stmt in statements:
                    db.execute(stmt)
                for name, cols in creates:
                    if db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]:
                        continue
                    fields = [c.strip() for c in cols.split(",") if c.strip()]
                    if not fields:
                        continue
                    rows = ",".join("(" + ",".join(_sample(c, i) for c in fields) + ")" for i in (0, 1))
                    db.execute(f"INSERT INTO {name} VALUES {rows}")
                db.commit()
                db.close()
            except sqlite3.Error:
                pass


_project_databases()


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts with an empty database (tests call db.init() to create the tables and demo data)."""
    path = os.environ.get("STORE_DB")
    if path and os.path.exists(path):
        os.remove(path)
    yield
