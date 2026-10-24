from cart import add_item, cart_total, remove_item

PRICES = {1: 12.0, 2: 4.5, 3: 7.99}


def test_add_item():
    assert add_item([], 1) == [1]
    assert add_item([1], 2) == [1, 2]


def test_add_ignores_duplicates():
    assert add_item([1, 2], 1) == [1, 2]


def test_add_returns_new_list():
    cart = [1]
    add_item(cart, 2)
    assert cart == [1]


def test_remove_item():
    assert remove_item([1, 2, 3], 2) == [1, 3]


def test_remove_missing_is_noop():
    assert remove_item([1, 2], 9) == [1, 2]
    assert remove_item([], 1) == []


def test_remove_returns_new_list():
    cart = [1, 2]
    remove_item(cart, 1)
    assert cart == [1, 2]


def test_total():
    assert cart_total([1, 2], PRICES) == 16.5


def test_total_is_rounded():
    assert cart_total([3, 3, 3], PRICES) == 23.97
    assert cart_total([1, 2, 3], PRICES) == 24.49


def test_empty_cart_totals_zero():
    assert cart_total([], PRICES) == 0.0
