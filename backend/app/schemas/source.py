from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel


class SourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    enabled: bool
    crawl_config: dict
    created_at: datetime

    class Config:
        from_attributes = True


class SourcePatch(BaseModel):
    enabled: bool
