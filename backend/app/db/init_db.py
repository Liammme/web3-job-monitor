from __future__ import annotations
from app.db.database import Base, engine
from app.models import crawl_run, job, job_score, notification, setting, source
from app.services.seed import seed_sources_if_empty


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_sources_if_empty()
