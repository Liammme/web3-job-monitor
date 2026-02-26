from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crawlers.base import NormalizedJob
from app.db.database import Base
from app.models.job import Job
from app.models.notification import Notification
from app.models.setting import Setting
from app.models.source import Source
from app.services import crawl_service
from app.services.crawl_service import run_crawl
from app.services.seed import default_notification_config, default_score_config


class FakeAdapter:
    def fetch(self):
        return [
            NormalizedJob(
                source_job_id="job-1",
                canonical_url="https://example.com/jobs/1",
                title="Senior Solidity Engineer",
                company="Acme",
                location="global",
                remote_type="remote",
                description="defi protocol",
            ),
            NormalizedJob(
                source_job_id="job-2",
                canonical_url="https://example.com/jobs/2",
                title="Blockchain Engineer",
                company="Beta",
                location="",
                remote_type="",
                description="",
            ),
            NormalizedJob(
                source_job_id="job-1",
                canonical_url="https://example.com/jobs/1",
                title="Senior Solidity Engineer",
                company="Acme",
                location="global",
                remote_type="remote",
                description="defi protocol",
            ),
        ]


class FakeNotifier:
    def __init__(self, *_args, **_kwargs):
        self.sent = []

    def build_single_payload(self, *args, **kwargs):
        return {"mode": "single"}

    def build_digest_payload(self, summary):
        return {"mode": "digest", "summary": summary}

    def send(self, payload):
        self.sent.append(payload)
        return True, "ok"


def test_run_crawl_dedupes_and_notifies(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    db.add(Source(name="web3career", base_url="https://web3.career", enabled=True, crawl_config={}))
    db.add(Setting(key="scoring", value=default_score_config()))
    db.add(Setting(key="notifications", value=default_notification_config()))
    db.commit()

    monkeypatch.setitem(crawl_service.ADAPTERS, "web3career", FakeAdapter)
    monkeypatch.setattr(crawl_service, "DiscordNotifier", FakeNotifier)

    result = run_crawl(db)

    assert result["new_jobs"] == 2
    assert result["high_priority_jobs"] == 1
    assert db.query(Job).count() == 2
    assert db.query(Notification).count() == 2  # single + digest
    assert len(result["company_summaries"]) == 2
    assert result["company_summaries"][0]["company"] == "Acme"
    assert result["company_summaries"][0]["main_source"] == "web3career"
