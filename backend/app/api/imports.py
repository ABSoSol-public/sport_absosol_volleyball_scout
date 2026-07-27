from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_writer
from app.db.session import get_db
from app.dvw import DvwParseError, parse_dvw
from app.dvw.importer import import_dvw
from app.models import User

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_SIZE = 5 * 1024 * 1024  # .dvw-Dateien sind typischerweise < 1 MB


@router.post("/dvw", status_code=201)
async def upload_dvw(
    file: UploadFile,
    db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> dict:
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "Datei zu groß für eine DVW-Scoutdatei.")
    try:
        parsed = parse_dvw(content)
    except DvwParseError as exc:
        raise HTTPException(422, str(exc)) from exc

    result = import_dvw(db, parsed)
    return {
        "match_id": result.match.id,
        "teams_created": result.teams_created,
        "players_created": result.players_created,
        "sets": result.sets_created,
        "rallies": result.rallies_created,
        "actions": result.actions_created,
    }
