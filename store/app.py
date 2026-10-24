"""The 3D asset store. Login and cart logic live in pieces/, this file only calls them."""
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
from pieces import auth, cart

HERE = Path(__file__).parent

app = FastAPI()
# A fixed key is fine for a one-user local demo; a real store would load it from a secret.
app.add_middleware(SessionMiddleware, secret_key="carve-out-demo-key", session_cookie="store_session")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")

db.init()


def render(request: Request, name: str, **context):
    """Render a page, passing the login state, cart size and any one-time message."""
    context.update(
        logged_in=auth.is_logged_in(request.session),
        cart_count=len(request.session.get("cart", [])),
        message=request.session.pop("message", None),
    )
    return templates.TemplateResponse(request, name, context)


def redirect(request: Request, url: str, message: str | None = None):
    if message:
        request.session["message"] = message
    return RedirectResponse(url, status_code=303)


@app.get("/")
def browse(request: Request):
    return render(request, "browse.html", assets=db.get_assets(), in_cart=request.session.get("cart", []))


@app.get("/login")
def login_page(request: Request):
    return render(request, "login.html", error=None)


@app.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    if auth.check_login(username, password, db.get_users()):
        request.session["username"] = username
        return redirect(request, "/", f"Welcome back, {username}.")
    return render(request, "login.html", error="Wrong username or password.")


@app.post("/logout")
def logout(request: Request):
    request.session.pop("username", None)
    return redirect(request, "/", "You're logged out.")


@app.post("/cart/add/{asset_id}")
def cart_add(request: Request, asset_id: int):
    request.session["cart"] = cart.add_item(request.session.get("cart", []), asset_id)
    return redirect(request, "/cart")


@app.post("/cart/remove/{asset_id}")
def cart_remove(request: Request, asset_id: int):
    request.session["cart"] = cart.remove_item(request.session.get("cart", []), asset_id)
    return redirect(request, "/cart")


@app.get("/cart")
def cart_page(request: Request):
    items = request.session.get("cart", [])
    assets = {a["id"]: a for a in db.get_assets()}
    prices = {asset_id: a["price"] for asset_id, a in assets.items()}
    return render(request, "cart.html",
                  items=[assets[i] for i in items if i in assets],
                  total=cart.cart_total(items, prices))


@app.post("/checkout")
def checkout(request: Request):
    if not auth.is_logged_in(request.session):
        return redirect(request, "/login", "Log in to check out.")
    items = request.session.get("cart", [])
    if not items:
        return redirect(request, "/cart", "Your cart is empty.")
    db.add_purchases(items)
    request.session["cart"] = []
    return redirect(request, "/profile", "Purchase complete (no real payment). Your download links are below.")


@app.get("/profile")
def profile(request: Request):
    if not auth.is_logged_in(request.session):
        return redirect(request, "/login", "Log in to see your profile.")
    return render(request, "profile.html", username=request.session["username"], purchases=db.get_purchases())


@app.get("/download/{purchase_id}")
def download(request: Request, purchase_id: int):
    if not auth.is_logged_in(request.session):
        return redirect(request, "/login", "Log in to download.")
    purchase = db.get_purchase(purchase_id)
    if purchase is None:
        raise HTTPException(404)
    return FileResponse(HERE / "static" / "assets" / purchase["image"], filename=purchase["image"])
