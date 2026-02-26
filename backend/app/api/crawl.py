from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.database import get_db
from app.services.crawl_service import run_crawl

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post("/trigger")
def trigger(_: str = Depends(require_user), db: Session = Depends(get_db)):
    digest = run_crawl(db)
    return {
        "success": True,
        "message": "crawl completed",
        "new_jobs": digest["new_jobs"],
        "high_priority_jobs": digest["high_priority_jobs"],
    }
