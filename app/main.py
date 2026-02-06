from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routes import router

app = FastAPI(title="漂-しるし-")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(router)

@app.get("/", response_class=HTMLResponse)
def index(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "error": error,
        },
    )
