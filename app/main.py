import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.logger import setup_logging
from app.middleware.logging_middleware import logging_middleware
from app.config import settings
from app.api.v1 import torrents, system, library, stash, whisparr, prowlarr, auth, search, trackers, watch, email, recommender, stats

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", extra={"version": "0.2.0"})
    init_db()
    logger.info("app_ready")
    yield
    logger.info("app_shutting_down")


app = FastAPI(title="Laura Suite API", version="0.2.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(logging_middleware)

app.include_router(torrents.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(stash.router, prefix="/api/v1")
app.include_router(whisparr.router, prefix="/api/v1")
app.include_router(prowlarr.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(trackers.router, prefix="/api/v1")
app.include_router(watch.router, prefix="/api/v1")
app.include_router(email.router, prefix="/api/v1")
app.include_router(recommender.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"app": "Laura Suite", "version": "0.2.0"}


