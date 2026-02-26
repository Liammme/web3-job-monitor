from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel


class CrawlRunOut(BaseModel):
    id: int
    source_id: int
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    new_count: int
    high_priority_count: int
    blocked_count: int
    status: str
    error_summary: str

    class Config:
        from_attributes = True
