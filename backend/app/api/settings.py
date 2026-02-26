from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.database import get_db
from app.schemas.score import ScoreConfig
from app.schemas.setting import NotificationSettings
from app.services.settings_service import get_setting, upsert_setting

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/scoring")
def get_scoring(_: str = Depends(require_user), db: Session = Depends(get_db)):
    return get_setting(db, "scoring")


@router.put("/scoring")
def put_scoring(body: ScoreConfig, _: str = Depends(require_user), db: Session = Depends(get_db)):
    return upsert_setting(db, "scoring", body.model_dump())


@router.get("/notifications")
def get_notifications(_: str = Depends(require_user), db: Session = Depends(get_db)):
    return get_setting(db, "notifications")


@router.put("/notifications")
def put_notifications(body: NotificationSettings, _: str = Depends(require_user), db: Session = Depends(get_db)):
    return upsert_setting(db, "notifications", body.model_dump())
