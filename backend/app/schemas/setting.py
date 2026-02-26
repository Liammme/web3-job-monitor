from __future__ import annotations
from pydantic import BaseModel


class NotificationSettings(BaseModel):
    discord_webhook_url: str = ""
    quiet_hours_start_utc: int | None = None
    quiet_hours_end_utc: int | None = None


class CrawlTriggerResponse(BaseModel):
    success: bool
    message: str
    new_jobs: int
    high_priority_jobs: int
