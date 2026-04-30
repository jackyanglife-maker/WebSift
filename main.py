"""FastAPI application entrypoint for WebSift."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.db import init_db

app = FastAPI(title="WebSift")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database tables on app startup."""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve the placeholder home page."""
    return templates.TemplateResponse("index.html", {"request": request})
