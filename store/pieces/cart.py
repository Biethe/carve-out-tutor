"""Cart piece: the cart is a list of asset IDs kept in the session."""


def add_item(cart: list[int], asset_id: int) -> list[int]:
    """Return a new cart with asset_id added. A digital asset is bought once, so duplicates are ignored."""
    if asset_id in cart:
        return list(cart)
    return cart + [asset_id]


def remove_item(cart: list[int], asset_id: int) -> list[int]:
    """Return a new cart without asset_id. Removing a missing ID changes nothing."""
    return [item for item in cart if item != asset_id]


def cart_total(cart: list[int], prices: dict[int, float]) -> float:
    """Sum of the prices of the items in the cart, rounded to 2 decimals."""
    return round(sum(prices[item] for item in cart), 2)
