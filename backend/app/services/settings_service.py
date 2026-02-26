from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.setting import Setting
from app.services.seed import default_notification_config, default_score_config


def get_setting(db: Session, key: str) -> dict:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        return row.value
    if key == "scoring":
        return default_score_config()
    if key == "notifications":
        return default_notification_config()
    return {}


def upsert_setting(db: Session, key: str, value: dict) -> dict:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        row = Setting(key=key, value=value, updated_at=datetime.utcnow())
        db.add(row)
    db.commit()
    db.refresh(row)
    return row.value
