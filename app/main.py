from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import torrents, system, library, stash, whisparr, prowlarr, auth

app = FastAPI(title="Laura Suite API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(torrents.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(stash.router, prefix="/api/v1")
app.include_router(whisparr.router, prefix="/api/v1")
app.include_router(prowlarr.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"app": "Laura Suite", "version": "0.1.0"}
