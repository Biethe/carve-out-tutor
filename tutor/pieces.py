"""The carvable pieces, in round order. Hand-written; reference code is pulled live from the store."""
import ast
from pathlib import Path

STORE = Path(__file__).parent.parent / "store"

PIECES = {
    "auth": {
        "title": "Authentication",
        "file": "auth.py",
        "test": "tests/test_auth.py",
        "summary": "The store's login logic: turning a password into a hash, checking a login attempt, and telling whether someone is logged in.",
        "stub": '''"""Authentication piece: password hashing, login check, session check."""


def hash_password(password: str) -> str:
    """Return the SHA-256 hex digest of the password."""
    # Your code here
    raise NotImplementedError


def check_login(username: str, password: str, users: dict[str, str]) -> bool:
    """True only if the user exists and the password hashes to the stored hash."""
    # Your code here
    raise NotImplementedError


def is_logged_in(session: dict) -> bool:
    """True if the session holds a username."""
    # Your code here
    raise NotImplementedError
''',
        "functions": [
            ("hash_password(password: str) -> str",
             "Takes the plain password and returns its SHA-256 hash as a 64-character hex string. Python's hashlib module does the hashing."),
            ("check_login(username: str, password: str, users: dict[str, str]) -> bool",
             "users maps each username to its stored password hash. Return True only if the user exists and the typed password hashes to that stored hash. An empty username or password returns False. Compare the two hashes with hmac.compare_digest."),
            ("is_logged_in(session: dict) -> bool",
             "session is a dict holding the visitor's session data. Return True if it contains a \"username\"."),
        ],
        "call_sites": [
            "POST /login (store/app.py, login) loads users from the database, calls check_login, and on True saves the username in the session.",
            "Every page (store/app.py, render) calls is_logged_in to show Log in or Profile in the header. checkout, profile and download use it to turn away visitors.",
            "On first start, store/db.py (init) calls hash_password to save the demo user's password hash.",
        ],
        "breaks": "If check_login is too loose, anyone can log in and check out. If it's too strict, the real user can't log in. If is_logged_in is wrong, logged-out visitors reach checkout and the profile, or logged-in users keep getting sent to the login page.",
        "references": [("app.py", "login"), ("app.py", "render"), ("app.py", "checkout"), ("db.py", "get_users"), ("db.py", "init")],
        "model_explanation": "hash_password turns the password into a fixed SHA-256 fingerprint (hex string), so the store keeps a hash instead of the real password, and the same input always gives the same hash. check_login rejects empty input, looks the username up in the users dict (unknown user means False), hashes the typed password and compares it with the stored hash using hmac.compare_digest, which takes the same time whether or not the hashes match, so an attacker can't learn the hash from timing. is_logged_in checks whether the session data holds a username; the login route puts it there after a successful check_login, and routes like checkout and profile use is_logged_in to block visitors who aren't logged in.",
    },
}


def reference_code(file: str, name: str) -> str:
    """Source of one top-level function in a store file, read live so it never goes stale."""
    source = (STORE / file).read_text()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            start = node.decorator_list[0].lineno if node.decorator_list else node.lineno
            return "\n".join(source.splitlines()[start - 1:node.end_lineno])
    return f"# {name} not found in {file}"


def task(piece: str) -> dict:
    """What the workspace shows for a piece: everything except the stub and grading text."""
    p = PIECES[piece]
    return {
        "id": piece,
        "title": p["title"],
        "file": f"store/pieces/{p['file']}",
        "summary": p["summary"],
        "functions": [{"signature": s, "description": d} for s, d in p["functions"]],
        "call_sites": p["call_sites"],
        "breaks": p["breaks"],
        "references": [{"file": f"store/{f}", "name": n, "code": reference_code(f, n)} for f, n in p["references"]],
    }
