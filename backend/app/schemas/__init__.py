from __future__ import annotations
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.job import JobOut
from app.schemas.run import CrawlRunOut
from app.schemas.score import JobScoreOut, ScoreConfig
from app.schemas.setting import CrawlTriggerResponse, NotificationSettings
from app.schemas.source import SourceOut, SourcePatch

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "JobOut",
    "CrawlRunOut",
    "JobScoreOut",
    "ScoreConfig",
    "CrawlTriggerResponse",
    "NotificationSettings",
    "SourceOut",
    "SourcePatch",
]
