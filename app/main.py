import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.auth.dependencies import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.logger import setup_logging
from app.middleware.logging_middleware import logging_middleware
from app.config import settings
from app.api.v1 import torrents, system, library, stash, whisparr, prowlarr, auth, search, trackers, watch, email, recommender, stats, metrics, stashdb_search, standard_search_history
from app.library.standard_search import api as lib_std_search
from app.library.common.service import initialize_search

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", extra={"version": "0.2.0"})
    init_db()
    initialize_search()
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

secure_routers = [
    torrents.router,
    system.router,
    library.router,
    stash.router,
    whisparr.router,
    prowlarr.router,
    search.router,
    trackers.router,
    watch.router,
    email.router,
    recommender.router,
    stats.router,
    metrics.router,
    lib_std_search.router,
    stashdb_search.router,
    standard_search_history.router,
]
for r in secure_routers:
    app.include_router(r, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(auth.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"app": "Laura Suite", "version": "0.2.0"}


