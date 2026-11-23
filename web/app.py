"""Ứng dụng web local (FastAPI + giao diện React đã build trong web/static/dist)."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from web.routes import backtest, journal, market, news, settings, status
from web.state import AppState

STATIC = Path(__file__).resolve().parent / "static"
INDEX = STATIC / "dist" / "index.html"
MISSING_BUILD = """<!doctype html><meta charset="utf-8"><title>GoldBot</title>
<body style="font-family:sans-serif;background:#181a21;color:#c9ccd3;padding:40px">
<h2>Chưa build giao diện</h2><p>Chạy: <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code></p></body>"""


def create_app(root: Path, config_path: Path) -> FastAPI:
    app = FastAPI(title="GoldBot", docs_url="/api/docs", redoc_url=None)
    app.state.app_state = AppState(root, config_path)
    for module in (status, market, journal, backtest, news, settings):
        app.include_router(module.router)
    STATIC.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False, response_model=None)
    def index() -> FileResponse | HTMLResponse:
        if not INDEX.exists():
            return HTMLResponse(MISSING_BUILD)
        return FileResponse(INDEX, headers={"Cache-Control": "no-cache"})

    return app
