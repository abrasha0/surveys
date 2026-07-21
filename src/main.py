import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import config
from logger import setup_logging
from auth import auth_router
from routers.api import router as api_router
from worker import get_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(
        log_file=config.logging["file"],
        level=getattr(logging, config.logging["level"].upper(), logging.DEBUG),
    )
    yield
    worker = get_worker()
    if worker.state.is_running:
        await worker.stop()


app = FastAPI(title="AnkieterAI", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(api_router)

dist_path = Path(__file__).parent.parent / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
