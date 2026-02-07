from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .database import init_db, get_user_by_anon_id
from .routes import router

BASE_DIR = Path(__file__).resolve().parent  # = .../app
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="漂-しるし-")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(router)

@app.get("/", response_class=HTMLResponse)
def index(request: Request, error: str | None = None):
    anon_id = request.cookies.get("anon_id")
    user = get_user_by_anon_id(anon_id) if anon_id else None

    resp = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "error": error,
            "has_anon": bool(user),
        },
    )

    # ★cookieはあるけどDBにいない = stale cookie → 消す（おすすめ）
    if anon_id and not user:
        resp.delete_cookie("anon_id")

    return resp