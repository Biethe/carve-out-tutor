import hashlib

from auth import check_login, hash_password, is_logged_in

USERS = {"learner": hashlib.sha256(b"carve123").hexdigest()}


def test_hash_is_sha256_hex():
    assert hash_password("carve123") == hashlib.sha256(b"carve123").hexdigest()


def test_hash_is_stable_and_differs_per_password():
    assert hash_password("abc") == hash_password("abc")
    assert hash_password("abc") != hash_password("abd")


def test_correct_login():
    assert check_login("learner", "carve123", USERS) is True


def test_wrong_password():
    assert check_login("learner", "wrong", USERS) is False


def test_unknown_user():
    assert check_login("someone", "carve123", USERS) is False


def test_empty_fields():
    assert check_login("", "carve123", USERS) is False
    assert check_login("learner", "", USERS) is False
    assert check_login("", "", USERS) is False


def test_logged_in_session():
    assert is_logged_in({"username": "learner"}) is True


def test_logged_out_session():
    assert is_logged_in({}) is False
    assert is_logged_in({"cart": [1, 2]}) is False
