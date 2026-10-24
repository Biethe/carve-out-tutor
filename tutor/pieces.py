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
             "Takes the plain password and returns its SHA-256 hash as a 64-character hex string. Python's hashlib module does the hashing.",
             [("test_hash_is_sha256_hex", "Returns the SHA-256 hex digest of the password"),
              ("test_hash_is_stable_and_differs_per_password", "Same password always gives the same hash; different passwords give different hashes")]),
            ("check_login(username: str, password: str, users: dict[str, str]) -> bool",
             "users maps each username to its stored password hash. Return True only if the user exists and the typed password hashes to that stored hash. An empty username or password returns False. Compare the two hashes with hmac.compare_digest.",
             [("test_correct_login", "Right username and password returns True"),
              ("test_wrong_password", "Wrong password returns False"),
              ("test_unknown_user", "A username that doesn't exist returns False"),
              ("test_empty_fields", "An empty username or password returns False")]),
            ("is_logged_in(session: dict) -> bool",
             "session is a dict holding the visitor's session data. Return True if it contains a \"username\".",
             [("test_logged_in_session", "A session holding a username returns True"),
              ("test_logged_out_session", "An empty session, or one without a username, returns False")]),
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
    "cart": {
        "title": "Cart behavior",
        "file": "cart.py",
        "test": "tests/test_cart.py",
        "summary": "The shopping cart's logic: adding an asset, removing one, and adding up the total. The cart is a list of asset IDs kept in the visitor's session.",
        "stub": '''"""Cart piece: the cart is a list of asset IDs kept in the session."""


def add_item(cart: list[int], asset_id: int) -> list[int]:
    """Return a new cart with asset_id added. A digital asset is bought once, so duplicates are ignored."""
    # Your code here
    raise NotImplementedError


def remove_item(cart: list[int], asset_id: int) -> list[int]:
    """Return a new cart without asset_id. Removing a missing ID changes nothing."""
    # Your code here
    raise NotImplementedError


def cart_total(cart: list[int], prices: dict[int, float]) -> float:
    """Sum of the prices of the items in the cart, rounded to 2 decimals."""
    # Your code here
    raise NotImplementedError
''',
        "functions": [
            ("add_item(cart: list[int], asset_id: int) -> list[int]",
             "Returns a NEW list with asset_id added at the end. If it's already in the cart, return the same items unchanged (you only buy a digital asset once). Don't modify the list you were given.",
             [("test_add_item", "Adds the ID to the end of the cart"),
              ("test_add_ignores_duplicates", "Adding an ID that's already there changes nothing"),
              ("test_add_returns_new_list", "Leaves the original list unchanged")]),
            ("remove_item(cart: list[int], asset_id: int) -> list[int]",
             "Returns a NEW list without asset_id. If it isn't in the cart, nothing changes. Don't modify the list you were given.",
             [("test_remove_item", "Removes the ID from the cart"),
              ("test_remove_missing_is_noop", "Removing an ID that isn't there changes nothing"),
              ("test_remove_returns_new_list", "Leaves the original list unchanged")]),
            ("cart_total(cart: list[int], prices: dict[int, float]) -> float",
             "prices maps each asset ID to its price. Return the sum of the prices of the items in the cart, rounded to 2 decimals. An empty cart totals 0.0.",
             [("test_total", "Adds up the prices of the items in the cart"),
              ("test_total_is_rounded", "Rounds the total to 2 decimals"),
              ("test_empty_cart_totals_zero", "An empty cart totals 0.0")]),
        ],
        "call_sites": [
            "POST /cart/add/{id} and POST /cart/remove/{id} (store/app.py, cart_add and cart_remove) read the cart from the session, call add_item or remove_item, and save the returned list back into the session.",
            "GET /cart (store/app.py, cart_page) builds a prices dict from the database and calls cart_total to show the total.",
            "POST /checkout (store/app.py, checkout) buys every asset ID in the cart, then empties it.",
        ],
        "breaks": "If add_item allows duplicates, the learner buys the same asset twice. If remove_item fails, items can't be taken out of the cart. If cart_total is off, the cart shows the wrong price at checkout.",
        "references": [("app.py", "cart_add"), ("app.py", "cart_remove"), ("app.py", "cart_page"), ("app.py", "checkout")],
        "model_explanation": "The cart is just a list of asset IDs saved in the session, so each function takes the current list and returns a new one, which the route stores back in the session. add_item returns a copy of the list with the ID appended, or an unchanged copy if the ID is already there, because a digital asset is bought once. remove_item builds a new list that keeps every ID except the one being removed, so removing a missing ID changes nothing. Returning new lists instead of changing the original avoids surprising side effects on data someone else still holds. cart_total looks up each ID's price in the prices dict, adds them up and rounds to 2 decimals, because floating-point sums like 0.1 + 0.2 aren't exact and money should display cleanly; an empty cart sums to 0.0.",
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
        "functions": [{"signature": s, "description": d, "criteria": [{"test": t, "text": c} for t, c in crit]}
                      for s, d, crit in p["functions"]],
        "call_sites": p["call_sites"],
        "breaks": p["breaks"],
        "references": [{"file": f"store/{f}", "name": n, "code": reference_code(f, n)} for f, n in p["references"]],
    }
