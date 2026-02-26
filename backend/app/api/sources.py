from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.database import get_db
from app.models.source import Source
from app.schemas.source import SourcePatch

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(_: str = Depends(require_user), db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.id.asc()).all()


@router.patch("/{source_id}")
def patch_source(source_id: int, body: SourcePatch, _: str = Depends(require_user), db: Session = Depends(get_db)):
    row = db.query(Source).filter(Source.id == source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="source not found")
    row.enabled = body.enabled
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
