from __future__ import annotations
from datetime import datetime, timedelta

from sqlalchemy import desc, func
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


def _pick_company_url(raw_payload: dict, fallback_url: str) -> str:
    if isinstance(raw_payload, dict):
        for key in ("company_url", "company_website", "companySite", "company_link"):
            value = raw_payload.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value
    return fallback_url


def _contains_senior_signal(title: str) -> bool:
    lower = (title or "").lower()
    signals = ("senior", "staff", "lead", "principal", "manager", "director", "head")
    return any(s in lower for s in signals)


def _classify_hiring_status(run_new: int, recent_7d: int, prev_7d: int) -> str:
    if run_new <= 0:
        return "无新增"
    if prev_7d == 0 and recent_7d == run_new:
        return "新开招"
    if run_new >= 3 or (prev_7d > 0 and recent_7d >= max(3, int(prev_7d * 1.5))):
        return "扩招"
    return "持续招"


def _contact_priority_score(
    run_new: int, recent_7d: int, active_days_30d: int, source_count_30d: int, senior_ratio_30d: float
) -> int:
    heat = min(40.0, recent_7d * 6 + run_new * 4)
    continuity = min(20.0, active_days_30d * 3)
    source_confidence = min(20.0, source_count_30d * 8)
    senior_weight = min(20.0, senior_ratio_30d * 20)
    return int(round(heat + continuity + source_confidence + senior_weight))


def _clean_role_title(title: str) -> str:
    text = (title or "").splitlines()[0].strip()
    return " ".join(text.split())[:80]


def _build_company_summaries(db: Session, company_stats: dict[str, dict], now_utc: datetime) -> list[dict]:
    summaries: list[dict] = []
    for stat in company_stats.values():
        company = stat["company"]
        if company.strip().lower() == "unknown company":
            continue

        source_counts = stat["source_counts"]
        main_source = sorted(source_counts.items(), key=lambda x: (-x[1], x[0]))[0][0]
        avg_score = stat["score_sum"] / stat["new_jobs"] if stat["new_jobs"] else 0.0
        company_url = stat["company_url"]

        company_rows = (
            db.query(Job, JobScore)
            .outerjoin(JobScore, Job.id == JobScore.job_id)
            .filter(
                func.lower(Job.company) == company.lower(),
                Job.collected_at >= now_utc - timedelta(days=30),
            )
            .all()
        )
        recent_30d = len(company_rows)
        recent_7d = 0
        prev_7d = 0
        active_days_30d: set = set()
        senior_count_30d = 0
        source_ids_30d: set = set()

        for job, _score in company_rows:
            collected = job.collected_at
            if not collected:
                continue
            active_days_30d.add(collected.date())
            source_ids_30d.add(job.source_id)
            if _contains_senior_signal(job.title):
                senior_count_30d += 1
            if collected >= now_utc - timedelta(days=7):
                recent_7d += 1
            elif collected >= now_utc - timedelta(days=14):
                prev_7d += 1

        senior_ratio_30d = (senior_count_30d / recent_30d) if recent_30d else 0.0
        hiring_status = _classify_hiring_status(stat["new_jobs"], recent_7d, prev_7d)
        contact_priority = _contact_priority_score(
            stat["new_jobs"], recent_7d, len(active_days_30d), len(source_ids_30d), senior_ratio_30d
        )

        top_roles = sorted(
            stat["new_roles"],
            key=lambda x: (-x["score"], x["title"].lower()),
        )[:3]
        role_briefs = [
            {"title": _clean_role_title(item["title"]), "score": round(item["score"], 1), "url": item["url"]}
            for item in top_roles
        ]

        summaries.append(
            {
                "company": company,
                "hiring_status": hiring_status,
                "contact_priority": contact_priority,
                "new_jobs": stat["new_jobs"],
                "recent_7d": recent_7d,
                "recent_30d": recent_30d,
                "max_score": round(stat["max_score"], 1),
                "avg_score": round(avg_score, 1),
                "company_url": company_url,
                "main_source": main_source,
                "main_source_website": stat["source_websites"].get(main_source, ""),
                "top_roles": role_briefs,
            }
        )

    summaries.sort(key=lambda x: (-x["max_score"], -x["contact_priority"], -x["new_jobs"], x["company"].lower()))
    return summaries


def run_crawl(db: Session) -> dict:
    sources = db.query(Source).filter(Source.enabled.is_(True)).all()
    score_cfg = get_setting(db, "scoring")
    notify_cfg = get_setting(db, "notifications")
    scorer = Scorer(score_cfg)
    notifier = DiscordNotifier(notify_cfg.get("discord_webhook_url") or "")
    quiet_hours = _in_quiet_hours(notify_cfg)
    now_utc = datetime.utcnow()

    total_new = 0
    total_high = 0
    failed_sources: list[str] = []
    source_stats: list[dict] = []
    company_stats: dict[str, dict] = {}

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

                company_name = (record.company or "").strip() or "Unknown Company"
                company_key = company_name.lower()
                stat = company_stats.setdefault(
                    company_key,
                    {
                        "company": company_name,
                        "new_jobs": 0,
                        "max_score": 0.0,
                        "score_sum": 0.0,
                        "company_url": "",
                        "source_counts": {},
                        "source_websites": {},
                        "new_roles": [],
                    },
                )
                stat["new_jobs"] += 1
                stat["max_score"] = max(stat["max_score"], float(score_result.total_score))
                stat["score_sum"] += float(score_result.total_score)
                if not stat["company_url"]:
                    stat["company_url"] = _pick_company_url(record.raw_payload, record.canonical_url)
                stat["source_counts"][source.name] = stat["source_counts"].get(source.name, 0) + 1
                stat["source_websites"][source.name] = source.base_url
                stat["new_roles"].append(
                    {
                        "title": record.title,
                        "score": float(score_result.total_score),
                        "url": record.canonical_url,
                    }
                )

                if score_result.decision == "high":
                    high_count += 1
                    total_high += 1
                    if not quiet_hours:
                        company_url = _pick_company_url(record.raw_payload, record.canonical_url)
                        payload = notifier.build_single_payload(
                            {
                                "source_name": source.name,
                                "source_website": source.base_url,
                                "title": record.title,
                                "company": record.company,
                                "company_url": company_url,
                                "posted_at": record.posted_at,
                                "location": record.location,
                                "remote_type": record.remote_type,
                                "canonical_url": record.canonical_url,
                            },
                            {
                                "total_score": score_result.total_score,
                                "decision": score_result.decision,
                                "keyword_score": score_result.keyword_score,
                                "seniority_score": score_result.seniority_score,
                                "remote_bonus": score_result.remote_bonus,
                                "region_bonus": score_result.region_bonus,
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
        "company_summaries": _build_company_summaries(db, company_stats, now_utc),
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
