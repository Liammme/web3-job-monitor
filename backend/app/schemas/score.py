from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel


class JobScoreOut(BaseModel):
    total_score: float
    keyword_score: float
    seniority_score: float
    remote_bonus: float
    region_bonus: float
    decision: str
    scored_at: datetime

    class Config:
        from_attributes = True


class ScoreConfig(BaseModel):
    strong_keywords: dict[str, int]
    medium_keywords: dict[str, int]
    strong_cap: int
    medium_cap: int
    seniority: dict[str, int]
    remote_bonus: int
    global_bonus: int
    threshold: int
    reject_if_negative_and_below: int
    negative_keywords: list[str]
