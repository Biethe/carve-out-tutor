"""Authentication piece: password hashing, login check, session check."""
import hashlib
import hmac


def hash_password(password: str) -> str:
    """Return the SHA-256 hex digest of the password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_login(username: str, password: str, users: dict[str, str]) -> bool:
    """True only if the user exists and the password hashes to the stored hash."""
    if not username or not password:
        return False
    stored_hash = users.get(username)
    if stored_hash is None:
        return False
    # compare_digest takes the same time whether or not the strings match,
    # so an attacker can't guess the hash one character at a time.
    return hmac.compare_digest(stored_hash, hash_password(password))


def is_logged_in(session: dict) -> bool:
    """True if the session holds a username."""
    return bool(session.get("username"))
