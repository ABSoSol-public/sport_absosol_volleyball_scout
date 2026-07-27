from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, imports, live, matches, teams
from app.api.deps import get_current_user
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

app.include_router(auth.router, prefix=settings.api_prefix)
# Alle Fachrouten nur mit gültiger Session; Schreibrechte regeln die Endpunkte
# zusätzlich über require_writer (Rolle "viewer" = nur lesen).
protected = [Depends(get_current_user)]
app.include_router(teams.router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(matches.router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(live.router, prefix=settings.api_prefix, dependencies=protected)
app.include_router(imports.router, prefix=settings.api_prefix, dependencies=protected)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
