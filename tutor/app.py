"""The tutor app: serves the pages and the JSON API on localhost:8000."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tutor import runner

PAGES = Path(__file__).parent / "pages"


@asynccontextmanager
async def lifespan(app):
    yield
    runner.stop_store()  # don't leave the store running after the tutor stops


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def catalog():
    return FileResponse(PAGES / "catalog.html")


@app.get("/project")
def project():
    return FileResponse(PAGES / "project.html")


@app.post("/api/run")
def run():
    return runner.run_store(passed=[])
