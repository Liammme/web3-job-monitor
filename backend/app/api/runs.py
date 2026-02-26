from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.database import get_db
from app.services.crawl_service import list_runs

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def get_runs(
    limit: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    return list_runs(db, limit)
