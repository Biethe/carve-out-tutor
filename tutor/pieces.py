"""The carvable pieces: every .py file of the store, each rebuilt one function at a time.
Six functions have hand-written cards (below). Every other function is found with ast, and its card and tests are
written by the learner's AI the first time it's opened (tutor/cards.py). Reference code is pulled live from the store."""
import ast
from pathlib import Path

STORE = Path(__file__).parent.parent / "store"
ROOT = STORE.parent


def _stub(signature: str, docstring: str) -> str:
    return f'def {signature}:\n    """{docstring}"""\n    # Your code here\n    raise NotImplementedError\n'


HAND = {
    "auth": {
        "title": "Authentication",
        "file": "pieces/auth.py",
        "test": "tests/test_auth.py",
        "functions": [
            {
                "name": "hash_password",
                "signature": "hash_password(password: str) -> str",
                "description": "Turn the plain password into its SHA-256 hash, written as a 64-character hex string. Python's hashlib module does the hashing.",
                "stub": _stub("hash_password(password: str) -> str", "Return the SHA-256 hex digest of the password."),
                "criteria": [
                    ("test_hash_is_sha256_hex", "Returns the SHA-256 hex digest of the password"),
                    ("test_hash_is_stable_and_differs_per_password", "Same password gives the same hash; different passwords give different hashes"),
                ],
                "call_sites": [
                    "POST /signup (store/app.py, signup) calls it to save a new account's password hash.",
                    "On first start, store/db.py (init) calls it to save the demo user's password hash.",
                    "Your next function, check_login, will use it to hash the password someone types.",
                ],
                "breaks": "If it returns anything other than the SHA-256 hex string, a typed password never matches the stored hash, and nobody can log in.",
                "references": [("app.py", "signup"), ("db.py", "init")],
                "question": "Why does the store keep a hash of the password instead of the password itself?",
                "answer": "So the real password is never stored: anyone who reads the database only sees hashes, and a hash can't be turned back into the password. Logging in still works because the same password always gives the same hash, so the store hashes what you type and compares the two hashes.",
            },
            {
                "name": "check_login",
                "signature": "check_login(username: str, password: str, users: dict[str, str]) -> bool",
                "description": "users maps each username to its stored password hash. Return True only if the username exists and the typed password hashes to the stored hash. Compare the two hashes with hmac.compare_digest.",
                "stub": _stub("check_login(username: str, password: str, users: dict[str, str]) -> bool",
                              "True only if the user exists and the password hashes to the stored hash."),
                "criteria": [
                    ("test_correct_login", "Right username and password returns True"),
                    ("test_wrong_password", "Wrong password returns False"),
                    ("test_unknown_user", "A username that doesn't exist returns False"),
                    ("test_empty_fields", "An empty username or password returns False"),
                ],
                "call_sites": [
                    "POST /login (store/app.py, login) loads users from the database with get_users and calls check_login. On True, it saves the username in the session.",
                ],
                "breaks": "Too loose and anyone can log in and check out. Too strict and the real user can't log in.",
                "references": [("app.py", "login"), ("db.py", "get_users")],
                "question": "Why compare the two hashes with hmac.compare_digest instead of ==?",
                "answer": "== stops at the first character that differs, so a guess that matches more of the hash takes slightly longer to reject. An attacker timing many attempts could learn the hash piece by piece. hmac.compare_digest takes the same time whatever the input, so the timing gives nothing away.",
            },
            {
                "name": "is_logged_in",
                "signature": "is_logged_in(session: dict) -> bool",
                "description": "session is a dict with the visitor's session data. Return True if it holds a \"username\".",
                "stub": _stub("is_logged_in(session: dict) -> bool", "True if the session holds a username."),
                "criteria": [
                    ("test_logged_in_session", "A session holding a username returns True"),
                    ("test_logged_out_session", "An empty session, or one without a username, returns False"),
                ],
                "call_sites": [
                    "Every page (store/app.py, render) calls it to show Log in or Profile in the header.",
                    "checkout, profile and download call it to turn away visitors who aren't logged in.",
                ],
                "breaks": "Logged-out visitors reach checkout and the profile, or logged-in users keep getting sent to the login page.",
                "references": [("app.py", "login"), ("app.py", "checkout")],
                "question": "Where does the \"username\" in the session come from?",
                "answer": "The login route puts it there: when check_login returns True, login saves the username in the session (a signed cookie). Logging out removes it, so if it's there, someone logged in.",
            },
        ],
    },
    "cart": {
        "title": "Cart behavior",
        "file": "pieces/cart.py",
        "test": "tests/test_cart.py",
        "functions": [
            {
                "name": "add_item",
                "signature": "add_item(cart: list[int], asset_id: int) -> list[int]",
                "description": "The cart is a list of asset IDs. Return a NEW list with asset_id added at the end. If it's already in the cart, return the same items unchanged. Don't change the list you were given.",
                "stub": _stub("add_item(cart: list[int], asset_id: int) -> list[int]",
                              "Return a new cart with asset_id added. A digital asset is bought once, so duplicates are ignored."),
                "criteria": [
                    ("test_add_item", "Adds the ID to the end of the cart"),
                    ("test_add_ignores_duplicates", "Adding an ID that's already there changes nothing"),
                    ("test_add_returns_new_list", "Leaves the original list unchanged"),
                ],
                "call_sites": [
                    "POST /cart/add/{id} (store/app.py, cart_add) reads the cart from the session, calls add_item, and saves the returned list back.",
                ],
                "breaks": "If it allows duplicates, you can buy the same asset twice.",
                "references": [("app.py", "cart_add")],
                "question": "Why does add_item return a new list instead of changing the one it was given?",
                "answer": "The list belongs to whoever called the function, here the session. Returning a new list avoids surprising changes to data someone else still holds, and lets the caller decide what to keep: the route saves the returned list back into the session.",
            },
            {
                "name": "remove_item",
                "signature": "remove_item(cart: list[int], asset_id: int) -> list[int]",
                "description": "Return a NEW list without asset_id. If it isn't in the cart, nothing changes. Don't change the list you were given.",
                "stub": _stub("remove_item(cart: list[int], asset_id: int) -> list[int]",
                              "Return a new cart without asset_id. Removing a missing ID changes nothing."),
                "criteria": [
                    ("test_remove_item", "Removes the ID from the cart"),
                    ("test_remove_missing_is_noop", "Removing an ID that isn't there changes nothing"),
                    ("test_remove_returns_new_list", "Leaves the original list unchanged"),
                ],
                "call_sites": [
                    "POST /cart/remove/{id} (store/app.py, cart_remove) calls remove_item and saves the returned list in the session.",
                ],
                "breaks": "Items can't be taken out of the cart.",
                "references": [("app.py", "cart_remove")],
                "question": "What happens if someone removes an asset that isn't in the cart, and why is that okay?",
                "answer": "Nothing changes: the new list keeps every ID except the removed one, and there isn't one. That's okay because the goal, \"this asset is not in the cart\", is already true, so there's no need for an error, for example when the remove button is clicked twice.",
            },
            {
                "name": "cart_total",
                "signature": "cart_total(cart: list[int], prices: dict[int, float]) -> float",
                "description": "prices maps each asset ID to its price. Return the sum of the prices of the items in the cart, rounded to 2 decimals. An empty cart is 0.0.",
                "stub": _stub("cart_total(cart: list[int], prices: dict[int, float]) -> float",
                              "Sum of the prices of the items in the cart, rounded to 2 decimals."),
                "criteria": [
                    ("test_total", "Adds up the prices of the items in the cart"),
                    ("test_total_is_rounded", "Rounds the total to 2 decimals"),
                    ("test_empty_cart_totals_zero", "An empty cart totals 0.0"),
                ],
                "call_sites": [
                    "GET /cart (store/app.py, cart_page) builds prices from the database and calls cart_total to show the total.",
                ],
                "breaks": "The cart shows the wrong price.",
                "references": [("app.py", "cart_page")],
                "question": "Why round the total to 2 decimals?",
                "answer": "Computers store decimals like 0.1 in binary, which isn't exact, so sums can come out as 24.490000000000002. Money only has cents, so rounding to 2 decimals gives the exact amount to show and charge.",
            },
        ],
    },
}


TITLES = {"app.py": "The web app's pages and forms", "db.py": "The database"}


def _discover() -> dict:
    """Every store file is a piece, every top-level function in it carvable. Hand-written cards win."""
    pieces = {}
    for path in sorted(STORE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        file = str(path.relative_to(STORE))
        key = path.stem
        hand = HAND.get(key, {})
        tree = ast.parse(path.read_text())
        known = {f["name"]: f for f in hand.get("functions", [])}
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                functions.append(known.get(node.name) or _auto(node))
        pieces[key] = {"title": hand.get("title") or TITLES.get(file, file), "file": file,
                       "test": hand.get("test"), "functions": functions}
    return {k: pieces[k] for k in [*HAND, *sorted(set(pieces) - set(HAND))]}  # the hand-made rounds first


def _auto(node: ast.FunctionDef) -> dict:
    """A card from the code alone. tutor/cards.py adds the AI-written description, question and tests later."""
    signature = next(line for line in ast.unparse(node).splitlines() if line.startswith(("def ", "async def ")))
    signature = signature.removeprefix("async ").removeprefix("def ").removesuffix(":")
    doc = ast.get_docstring(node) or ""
    return {"name": node.name, "signature": signature, "description": doc, "auto": True,
            "stub": _stub(signature, doc.split("\n")[0] or "Your code here."),
            "criteria": [], "call_sites": [], "breaks": "", "references": [], "question": "", "answer": ""}


PIECES = _discover()


def function(piece: str, name: str) -> dict:
    """A function's card: hand-written, or found by ast plus what the AI wrote for it (if it has been prepared)."""
    base = next(f for f in PIECES[piece]["functions"] if f["name"] == name)
    if not base.get("auto"):
        return base
    from tutor import cards  # imported here: cards needs this module
    return {**base, **(cards.load(piece, name) or {})}


def _function_spans(source: str, decorators: bool = True) -> dict[str, tuple[int, int]]:
    """1-based (first, last) line of each top-level function, from its decorators or from its `def` line."""
    return {n.name: (n.decorator_list[0].lineno if n.decorator_list and decorators else n.lineno, n.end_lineno)
            for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}


def reference_code(file: str, name: str) -> str:
    """Source of one top-level function in a store file, read live so it never goes stale."""
    source = (STORE / file).read_text()
    span = _function_spans(source).get(name)
    if span is None:
        return f"# {name} not found in {file}"
    return "\n".join(source.splitlines()[span[0] - 1:span[1]])


def assemble(piece: str, snippets: dict[str, str]) -> str:
    """The piece's file with the learner's functions swapped in for the AI's.
    Anything in a snippet (imports, helpers) goes where the original function was."""
    source = (STORE / PIECES[piece]["file"]).read_text()
    lines = source.splitlines()
    spans = _function_spans(source, decorators=False)  # a route's @app.get(...) stays; the learner writes the def
    for name in sorted(snippets, key=lambda n: spans[n][0], reverse=True):  # bottom-up keeps line numbers valid
        first, last = spans[name]
        lines[first - 1:last] = snippets[name].rstrip("\n").splitlines()
    return "\n".join(lines) + "\n"


def task(piece: str, name: str) -> dict:
    """What the workspace shows for one function, split into the task and what to read."""
    p, f = PIECES[piece], function(piece, name)
    return {
        "piece": p["title"],
        "file": f"store/{p['file']}",
        "name": name,
        "signature": f["signature"],
        "description": f["description"],
        "criteria": [{"test": t, "text": c} for t, c in f["criteria"]],
        "call_sites": f["call_sites"],
        "breaks": f["breaks"],
        "references": [{"file": f"store/{file}", "name": n, "code": reference_code(file, n)} for file, n in f["references"]],
    }
