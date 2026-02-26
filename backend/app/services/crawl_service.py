from __future__ import annotations
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crawlers.registry import ADAPTERS
from app.models.crawl_run import CrawlRun
from app.models.job import Job
from app.models.job_score import JobScore
from app.models.notification import Notification
from app.models.source import Source
from app.services.notifier import DiscordNotifier
from app.services.scoring import Scorer
from app.services.settings_service import get_setting
from app.utils.hash import job_fallback_hash


def _in_quiet_hours(cfg: dict) -> bool:
    start = cfg.get("quiet_hours_start_utc")
    end = cfg.get("quiet_hours_end_utc")
    if start is None or end is None:
        return False

    hour = datetime.utcnow().hour
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def run_crawl(db: Session) -> dict:
    sources = db.query(Source).filter(Source.enabled.is_(True)).all()
    score_cfg = get_setting(db, "scoring")
    notify_cfg = get_setting(db, "notifications")
    scorer = Scorer(score_cfg)
    notifier = DiscordNotifier(notify_cfg.get("discord_webhook_url") or "")
    quiet_hours = _in_quiet_hours(notify_cfg)

    total_new = 0
    total_high = 0
    failed_sources: list[str] = []
    source_stats: list[dict] = []

    for source in sources:
        run = CrawlRun(source_id=source.id, started_at=datetime.utcnow(), status="running")
        db.add(run)
        db.commit()
        db.refresh(run)

        fetched_count = 0
        new_count = 0
        high_count = 0

        try:
            adapter_cls = ADAPTERS.get(source.name)
            if not adapter_cls:
                raise ValueError(f"missing adapter for source={source.name}")

            adapter = adapter_cls()
            jobs = adapter.fetch()
            fetched_count = len(jobs)

            for normalized in jobs:
                fallback_hash = None
                if not normalized.source_job_id:
                    fallback_hash = job_fallback_hash(normalized.canonical_url, normalized.title, normalized.company)

                existing = None
                if normalized.source_job_id:
                    existing = (
                        db.query(Job)
                        .filter(Job.source_id == source.id, Job.source_job_id == normalized.source_job_id)
                        .first()
                    )
                if not existing:
                    hash_to_use = fallback_hash or job_fallback_hash(
                        normalized.canonical_url,
                        normalized.title,
                        normalized.company,
                    )
                    existing = db.query(Job).filter(Job.source_id == source.id, Job.fallback_hash == hash_to_use).first()

                if existing:
                    existing.is_new = False
                    continue

                record = Job(
                    source_id=source.id,
                    source_job_id=normalized.source_job_id,
                    fallback_hash=fallback_hash
                    or job_fallback_hash(normalized.canonical_url, normalized.title, normalized.company),
                    canonical_url=normalized.canonical_url,
                    title=normalized.title,
                    company=normalized.company,
                    location=normalized.location,
                    remote_type=normalized.remote_type,
                    employment_type=normalized.employment_type,
                    description=normalized.description,
                    posted_at=normalized.posted_at,
                    collected_at=datetime.utcnow(),
                    raw_payload=normalized.raw_payload,
                    is_new=True,
                )
                db.add(record)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    continue

                db.refresh(record)
                new_count += 1
                total_new += 1

                score_result = scorer.score(
                    {
                        "title": record.title,
                        "description": record.description,
                        "location": record.location,
                        "remote_type": record.remote_type,
                    }
                )
                score_row = JobScore(
                    job_id=record.id,
                    total_score=score_result.total_score,
                    keyword_score=score_result.keyword_score,
                    seniority_score=score_result.seniority_score,
                    remote_bonus=score_result.remote_bonus,
                    region_bonus=score_result.region_bonus,
                    decision=score_result.decision,
                    scored_at=datetime.utcnow(),
                )
                db.add(score_row)
                db.commit()

                if score_result.decision == "high":
                    high_count += 1
                    total_high += 1
                    if not quiet_hours:
                        payload = notifier.build_single_payload(
                            {
                                "source_name": source.name,
                                "title": record.title,
                                "company": record.company,
                                "location": record.location,
                                "remote_type": record.remote_type,
                                "canonical_url": record.canonical_url,
                            },
                            {
                                "total_score": score_result.total_score,
                                "decision": score_result.decision,
                                "matched_keywords": score_result.matched_keywords,
                            },
                            run.id,
                        )
                        ok, msg = notifier.send(payload)
                        db.add(
                            Notification(
                                job_id=record.id,
                                channel="discord",
                                mode="single",
                                status="sent" if ok else "failed",
                                error="" if ok else msg,
                            )
                        )
                        db.commit()

            run.status = "success"
            run.fetched_count = fetched_count
            run.new_count = new_count
            run.high_priority_count = high_count
            run.finished_at = datetime.utcnow()
            db.add(run)
            db.commit()

            source_stats.append(
                {
                    "source": source.name,
                    "fetched": fetched_count,
                    "new": new_count,
                    "high": high_count,
                    "status": "success",
                }
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            run.status = "failed"
            run.error_summary = str(exc)[:2000]
            run.finished_at = datetime.utcnow()
            db.add(run)
            db.commit()
            failed_sources.append(source.name)
            source_stats.append(
                {
                    "source": source.name,
                    "fetched": fetched_count,
                    "new": new_count,
                    "high": high_count,
                    "status": "failed",
                }
            )

    digest = {
        "new_jobs": total_new,
        "high_priority_jobs": total_high,
        "failed_sources": failed_sources,
        "source_stats": source_stats,
    }

    if not quiet_hours:
        payload = notifier.build_digest_payload(digest)
        ok, msg = notifier.send(payload)
        db.add(
            Notification(
                job_id=None,
                channel="discord",
                mode="digest",
                status="sent" if ok else "failed",
                error="" if ok else msg,
            )
        )
        db.commit()

    return digest


def list_runs(db: Session, limit: int = 100) -> list[CrawlRun]:
    return db.query(CrawlRun).order_by(desc(CrawlRun.started_at)).limit(limit).all()
