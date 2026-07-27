from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import live, matches, teams
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="ABSoSol Volleyball Scout API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teams.router, prefix=settings.api_prefix)
app.include_router(matches.router, prefix=settings.api_prefix)
app.include_router(live.router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
