from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.setting import Setting
from app.models.source import Source


def default_score_config() -> dict:
    return {
        "strong_keywords": {
            "solidity": 12,
            "smart contract": 12,
            "protocol": 12,
            "defi": 12,
            "mev": 12,
            "rollup": 12,
            "zk": 12,
            "rust": 12,
            "evm": 12,
        },
        "medium_keywords": {
            "web3": 6,
            "crypto": 6,
            "blockchain": 6,
            "wallet": 6,
            "node": 6,
        },
        "strong_cap": 60,
        "medium_cap": 30,
        "seniority": {
            "senior": 20,
            "staff": 20,
            "principal": 20,
            "lead": 20,
            "mid": 10,
            "junior": 0,
            "intern": 0,
        },
        "remote_bonus": 15,
        "global_bonus": 5,
        "threshold": 70,
        "reject_if_negative_and_below": 80,
        "negative_keywords": ["sales", "business development", "bd", "account executive"],
    }


def default_notification_config() -> dict:
    return {
        "discord_webhook_url": settings.discord_webhook_url,
        "quiet_hours_start_utc": None,
        "quiet_hours_end_utc": None,
    }


def seed_sources_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(Source).count() == 0:
            rows = [
                Source(name="linkedin", base_url="https://www.linkedin.com/jobs", enabled=True, crawl_config={}),
                Source(name="cryptojobslist", base_url="https://cryptojobslist.com", enabled=True, crawl_config={}),
                Source(name="web3career", base_url="https://web3.career", enabled=True, crawl_config={}),
                Source(name="wellfound", base_url="https://wellfound.com", enabled=True, crawl_config={}),
                Source(name="remote3", base_url="https://remote3.co", enabled=True, crawl_config={}),
            ]
            db.add_all(rows)

        keys = {s.key for s in db.query(Setting).all()}
        if "scoring" not in keys:
            db.add(Setting(key="scoring", value=default_score_config(), updated_at=datetime.utcnow()))
        if "notifications" not in keys:
            db.add(Setting(key="notifications", value=default_notification_config(), updated_at=datetime.utcnow()))

        db.commit()
    finally:
        db.close()
