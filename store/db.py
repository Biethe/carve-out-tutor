"""SQLite helpers for the store, plus seed data (one user, eight assets)."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from pieces.auth import hash_password

DB_PATH = os.environ.get("STORE_DB", str(Path(__file__).parent / "store.db"))

ASSETS = [
    ("Low-poly Fox", "model", 12.00, "fox.svg"),
    ("Sci-fi Cargo Crate", "model", 4.50, "crate.svg"),
    ("Medieval Longsword", "model", 7.99, "sword.svg"),
    ("Robot Walk Cycle", "animation", 9.00, "robot-walk.svg"),
    ("Dragon Flight Loop", "animation", 15.50, "dragon-flight.svg"),
    ("Floating Islands", "world", 24.00, "islands.svg"),
    ("Neon City Block", "world", 19.99, "neon-city.svg"),
    ("Forest Clearing", "world", 14.25, "forest.svg"),
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    """Create the tables and seed them the first time the store starts."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assets (id INTEGER PRIMARY KEY, name TEXT, kind TEXT, price REAL, image TEXT);
            CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY, asset_id INTEGER, bought_at TEXT);
        """)
        if not conn.execute("SELECT 1 FROM users").fetchone():
            conn.execute("INSERT INTO users VALUES (?, ?)", ("learner", hash_password("carve123")))
            conn.executemany("INSERT INTO assets (name, kind, price, image) VALUES (?, ?, ?, ?)", ASSETS)


def get_users() -> dict[str, str]:
    with connect() as conn:
        return {r["username"]: r["password_hash"] for r in conn.execute("SELECT * FROM users")}


def get_assets() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM assets ORDER BY id").fetchall()


def add_purchases(asset_ids: list[int]):
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        conn.executemany("INSERT INTO purchases (asset_id, bought_at) VALUES (?, ?)", [(a, now) for a in asset_ids])


def get_purchases() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("""
            SELECT purchases.id, purchases.bought_at, assets.name, assets.kind, assets.image
            FROM purchases JOIN assets ON assets.id = purchases.asset_id
            ORDER BY purchases.id DESC
        """).fetchall()


def get_purchase(purchase_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("""
            SELECT purchases.id, assets.name, assets.image
            FROM purchases JOIN assets ON assets.id = purchases.asset_id
            WHERE purchases.id = ?
        """, (purchase_id,)).fetchone()
