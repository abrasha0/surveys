import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Modules import each other as top-level packages (config, worker, ...), so make
# src/backend importable regardless of the working directory uvicorn starts in.
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config import config, APP_ROOT
from logger import setup_logging
from auth import auth_router, is_password_configured
from routers.api import router as api_router
from worker import get_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(
        log_file=config.logging["file"],
        level=getattr(logging, config.logging["level"].upper(), logging.DEBUG),
    )
    if not is_password_configured():
        message = (
            "app.password is empty. Set a password in config.yaml "
            "(or the ANKIETER_APP_PASSWORD environment variable) before starting the server."
        )
        logging.getLogger("app").critical(message)
        raise RuntimeError(message)
    worker = get_worker()
    surveys_dir = config.app.get("surveys_dir")
    if surveys_dir:
        dir_path = Path(surveys_dir)
        if dir_path.is_dir():
            from ingestion.file_grouping import scan_survey_directory
            groups = scan_survey_directory(dir_path)
            if groups:
                worker.state.ensure_from_cache(groups)
    yield
    if worker.state.is_running:
        await worker.stop()


app = FastAPI(title="AnkieterAI", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(api_router)

_dist_paths = [
    APP_ROOT / "working_vault" / "dist",
    APP_ROOT / "src" / "frontend" / "dist",
]
_dist_path = None
for _p in _dist_paths:
    if _p.exists():
        _dist_path = _p
        break

if _dist_path:
    app.mount("/", StaticFiles(directory=str(_dist_path), html=True), name="static")

    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        response = await call_next(request)
        if response.status_code == 404 and not request.url.path.startswith("/api/"):
            index_path = _dist_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
        return response
else:
    @app.get("/", response_class=HTMLResponse)
    async def no_frontend():
        return """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>AnkieterAI</title></head>
<body style="font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f5f5f5">
<div style="text-align:center;padding:2rem;background:white;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:520px">
<h1>AnkieterAI</h1>
<p>The frontend has not been built yet.</p>
<p><strong>Build and start it with</strong> (Windows / macOS and Linux):</p>
<pre style="background:#eee;padding:1rem;border-radius:4px;text-align:left;overflow-x:auto">.\\scripts\\run_prod.ps1
scripts/run_prod.sh</pre>
<p style="font-size:0.85rem;color:#666">or, for development:</p>
<pre style="background:#eee;padding:1rem;border-radius:4px;text-align:left;overflow-x:auto">.\\scripts\\run_dev.ps1
scripts/run_dev.sh</pre>
<p style="font-size:0.85rem;color:#666">(the frontend is served at <code>http://localhost:5173</code>)</p>
</div></body></html>
"""
