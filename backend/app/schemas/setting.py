from __future__ import annotations
from pydantic import BaseModel


class NotificationSettings(BaseModel):
    discord_webhook_url: str = ""
    discord_bot_token: str = ""
    discord_channel_id: str = ""
    quiet_hours_start_utc: int | None = None
    quiet_hours_end_utc: int | None = None
    daily_job_push_limit: int = 50


class CrawlTriggerResponse(BaseModel):
    success: bool
    message: str
    new_jobs: int
    high_priority_jobs: int
