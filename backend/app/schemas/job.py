from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel

from app.schemas.score import JobScoreOut


class JobOut(BaseModel):
    id: int
    source_id: int
    source_job_id: str | None
    canonical_url: str
    title: str
    company: str
    location: str
    remote_type: str
    employment_type: str
    description: str
    posted_at: datetime | None
    collected_at: datetime
    is_new: bool
    score: JobScoreOut | None = None

    class Config:
        from_attributes = True
