from __future__ import annotations
from datetime import datetime, timedelta, timezone
import re

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

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TELEGRAM_RE = re.compile(r"(https?://t\.me/[A-Za-z0-9_]+|@[A-Za-z0-9_]{5,})")
URL_RE = re.compile(r"https?://[^\s<>()]+")


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


def _sanitize_url(url: str) -> str:
    cleaned = (url or "").strip()
    if cleaned.endswith((".", ",", ";", ")", "]")):
        cleaned = cleaned[:-1]
    return cleaned


def _normalize_role_title(text: str) -> str:
    text = (text or "").strip()
    text = text.lstrip("-•*·\t ")
    text = re.sub(r"\s+", " ", text)
    return text[:90]


def _looks_like_role(text: str) -> bool:
    lower = text.lower()
    if len(text) < 3:
        return False
    noise_markers = ("以下岗位", "投递", "联系", "招聘需求", "岗位职责", "岗位要求")
    if any(marker in text for marker in noise_markers):
        return False
    role_markers = (
        "engineer",
        "developer",
        "manager",
        "director",
        "analyst",
        "lead",
        "architect",
        "designer",
        "solidity",
        "backend",
        "frontend",
        "full stack",
        "product",
        "运营",
        "工程师",
        "产品",
        "经理",
        "总监",
        "负责人",
        "研究员",
        "分析师",
        "开发",
        "设计",
        "算法",
        "增长",
        "商务",
        "BD",
    )
    return any(marker in lower for marker in role_markers) or any(marker in text for marker in role_markers)


def _extract_role_candidates(title: str, description: str) -> list[str]:
    text = "\n".join([title or "", (description or "")[:1200]])
    rough_lines = re.split(r"[\n\r]+", text)
    candidates: list[str] = []

    for line in rough_lines:
        stripped = line.strip()
        if not stripped:
            continue
        for part in re.split(r"[；;|]+", stripped):
            normalized = _normalize_role_title(part)
            if not normalized:
                continue
            if _looks_like_role(normalized):
                candidates.append(normalized)

    if not candidates:
        fallback = _normalize_role_title((title or "").splitlines()[0] if title else "")
        if fallback:
            candidates.append(fallback)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:6]


def _extract_contact_clues(description: str, raw_payload: dict, company_url: str, canonical_url: str) -> dict:
    text = description or ""
    emails = set(EMAIL_RE.findall(text))
    telegrams = set(TELEGRAM_RE.findall(text))
    urls = {_sanitize_url(x) for x in URL_RE.findall(text)}

    if isinstance(raw_payload, dict):
        for value in raw_payload.values():
            if isinstance(value, str):
                emails.update(EMAIL_RE.findall(value))
                telegrams.update(TELEGRAM_RE.findall(value))
                urls.update({_sanitize_url(x) for x in URL_RE.findall(value)})

    if company_url.startswith("http"):
        urls.add(company_url)
    if canonical_url.startswith("http"):
        urls.add(canonical_url)

    career_urls = {
        u
        for u in urls
        if u.startswith("http") and any(k in u.lower() for k in ("job", "career", "apply", "recruit", "hiring"))
    }
    if canonical_url.startswith("http"):
        career_urls.add(canonical_url)

    return {
        "emails": sorted(emails),
        "telegrams": sorted(telegrams),
        "career_urls": sorted(career_urls),
    }


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


def _contact_recommendation_label(contact_priority: int, hiring_status: str) -> str:
    if hiring_status in {"新开招", "扩招"} and contact_priority >= 65:
        return "建议立即联系"
    if contact_priority >= 45:
        return "建议本周联系"
    return "继续观察"


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


def _to_utc_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _is_recent_posted(posted_at: datetime | None, now_utc: datetime) -> bool:
    normalized = _to_utc_naive(posted_at)
    if normalized is None:
        return False
    # Keep a tiny future tolerance for source/server clock skew.
    if normalized > now_utc + timedelta(minutes=5):
        return False
    return normalized >= now_utc - timedelta(days=1)


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
        contact_action = _contact_recommendation_label(contact_priority, hiring_status)

        first_seen_at = (
            db.query(func.min(Job.collected_at)).filter(func.lower(Job.company) == company.lower()).scalar()
        )
        first_seen_text = first_seen_at.strftime("%Y-%m-%d") if first_seen_at else "N/A"

        dedup_role_map: dict[str, dict] = {}
        for role in stat["new_roles"]:
            normalized_title = _clean_role_title(role.get("title") or "")
            if not normalized_title:
                continue
            key = normalized_title.lower()
            existing = dedup_role_map.get(key)
            if existing is None or role["score"] > existing["score"]:
                dedup_role_map[key] = {
                    "title": normalized_title,
                    "score": float(role["score"]),
                    "url": role.get("url", ""),
                    "location": role.get("location", ""),
                    "employment_type": role.get("employment_type", ""),
                    "posted_at": role.get("posted_at"),
                }

        top_roles = sorted(
            dedup_role_map.values(),
            key=lambda x: (-x["score"], x["title"].lower()),
        )[:2]

        role_briefs = []
        for item in top_roles:
            posted_at = item.get("posted_at")
            if isinstance(posted_at, datetime):
                posted_text = posted_at.strftime("%Y-%m-%d %H:%M UTC")
            else:
                posted_text = "N/A"
            role_briefs.append(
                {
                    "title": item["title"],
                    "score": round(item["score"], 1),
                    "url": item["url"],
                    "location": item.get("location") or "N/A",
                    "employment_type": item.get("employment_type") or "N/A",
                    "posted_at": posted_text,
                }
            )
        job_titles = [item["title"] for item in top_roles if item.get("title")]
        if not job_titles:
            job_titles = [role.get("title", "") for role in dedup_role_map.values() if role.get("title")]
        job_titles = [x for x in job_titles if x][:3]

        clues = stat["contact_clues"]
        emails = sorted(clues["emails"])
        telegrams = sorted(clues["telegrams"])
        career_urls = sorted(clues["career_urls"])
        contact_clues = {
            "email": emails[0] if emails else "N/A",
            "telegram": telegrams[0] if telegrams else "N/A",
            "career_url": career_urls[0] if career_urls else company_url or "N/A",
        }

        summaries.append(
            {
                "company": company,
                "hiring_status": hiring_status,
                "contact_priority": contact_priority,
                "contact_action": contact_action,
                "new_jobs": stat["new_jobs"],
                "recent_7d": recent_7d,
                "recent_30d": recent_30d,
                "first_seen_at": first_seen_text,
                "max_score": round(stat["max_score"], 1),
                "avg_score": round(avg_score, 1),
                "company_url": company_url,
                "main_source": main_source,
                "main_source_website": stat["source_websites"].get(main_source, ""),
                "top_roles": role_briefs,
                "job_titles": job_titles,
                "contact_clues": contact_clues,
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
    high_job_details: list[dict] = []
    all_new_job_details: list[dict] = []

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
                normalized_posted_at = _to_utc_naive(normalized.posted_at)
                if not _is_recent_posted(normalized_posted_at, now_utc):
                    continue

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
                    posted_at=normalized_posted_at,
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

                posted_at_dt = record.posted_at or record.collected_at
                all_new_job_details.append(
                    {
                        "job_id": record.id,
                        "company": record.company or "N/A",
                        "title": _clean_role_title(record.title),
                        "score": float(score_result.total_score),
                        "seniority_score": float(score_result.seniority_score),
                        "senior_signal": 1 if _contains_senior_signal(record.title) else 0,
                        "source": source.name,
                        "source_website": source.base_url,
                        "url": record.canonical_url,
                        "location": record.location or "N/A",
                        "employment_type": record.employment_type or "N/A",
                        "posted_at": posted_at_dt.strftime("%Y-%m-%d %H:%M UTC"),
                        "posted_at_dt": posted_at_dt,
                    }
                )

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
                        "contact_clues": {"emails": set(), "telegrams": set(), "career_urls": set()},
                    },
                )
                stat["new_jobs"] += 1
                stat["max_score"] = max(stat["max_score"], float(score_result.total_score))
                stat["score_sum"] += float(score_result.total_score)
                if not stat["company_url"]:
                    stat["company_url"] = _pick_company_url(record.raw_payload, record.canonical_url)
                stat["source_counts"][source.name] = stat["source_counts"].get(source.name, 0) + 1
                stat["source_websites"][source.name] = source.base_url

                role_candidates = _extract_role_candidates(record.title, record.description)
                for role_title in role_candidates:
                    stat["new_roles"].append(
                        {
                            "title": role_title,
                            "score": float(score_result.total_score),
                            "url": record.canonical_url,
                            "location": record.location,
                            "employment_type": record.employment_type,
                            "posted_at": record.posted_at,
                        }
                    )

                clues = _extract_contact_clues(record.description, record.raw_payload, stat["company_url"], record.canonical_url)
                stat["contact_clues"]["emails"].update(clues["emails"])
                stat["contact_clues"]["telegrams"].update(clues["telegrams"])
                stat["contact_clues"]["career_urls"].update(clues["career_urls"])

                if score_result.decision == "high":
                    high_count += 1
                    total_high += 1
                    high_job_details.append(
                        {
                            "company": record.company or "N/A",
                            "title": _clean_role_title(record.title),
                            "score": round(float(score_result.total_score), 1),
                            "source": source.name,
                            "source_website": source.base_url,
                            "url": record.canonical_url,
                            "location": record.location or "N/A",
                            "employment_type": record.employment_type or "N/A",
                            "posted_at": record.posted_at.strftime("%Y-%m-%d %H:%M UTC"),
                        }
                    )

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
        "high_jobs": sorted(high_job_details, key=lambda x: (-x["score"], x["company"].lower(), x["title"].lower())),
    }

    daily_limit_raw = notify_cfg.get("daily_job_push_limit", 50)
    try:
        daily_limit = int(daily_limit_raw)
    except (TypeError, ValueError):
        daily_limit = 50
    daily_limit = max(1, daily_limit)

    sent_last_24h = (
        db.query(Notification)
        .filter(
            Notification.channel == "discord",
            Notification.mode == "job_digest_item",
            Notification.status == "sent",
            Notification.sent_at >= now_utc - timedelta(days=1),
        )
        .count()
    )
    remaining_quota = max(0, daily_limit - sent_last_24h)
    ranked_jobs = sorted(
        all_new_job_details,
        key=lambda x: (
            -x["score"],
            -x["seniority_score"],
            -x["senior_signal"],
            -x["posted_at_dt"].timestamp(),
            x["company"].lower(),
            x["title"].lower(),
        ),
    )
    selected_jobs = ranked_jobs[:remaining_quota]
    deferred_jobs = ranked_jobs[remaining_quota:]

    selected_source_stats: dict[str, int] = {}
    for item in selected_jobs:
        selected_source_stats[item["source"]] = selected_source_stats.get(item["source"], 0) + 1

    digest.update(
        {
            "daily_job_push_limit": daily_limit,
            "sent_last_24h": sent_last_24h,
            "remaining_quota": remaining_quota,
            "candidate_jobs": len(ranked_jobs),
            "selected_jobs": [
                {k: v for k, v in item.items() if k != "posted_at_dt"}
                for item in selected_jobs
            ],
            "selected_jobs_count": len(selected_jobs),
            "selected_source_stats": selected_source_stats,
            "deferred_jobs_count": len(deferred_jobs),
            "deferred_jobs": [{"company": x["company"], "title": x["title"]} for x in deferred_jobs[:200]],
        }
    )

    # Send digest as multiple clear messages to improve readability.
    payloads = notifier.build_digest_payloads(digest)
    send_errors: list[str] = []
    for payload in payloads:
        ok, msg = notifier.send(payload)
        if not ok:
            send_errors.append(msg)

    end_push_sent = False
    end_push_status = "skipped"
    end_push_error = ""
    if not send_errors:
        end_ok, end_msg = notifier.send({"content": "[END_OF_PUSH] 今日岗位推送结束，请 <@1473632297671725096> 生成今日报告"})
        end_push_sent = end_ok
        end_push_status = "sent" if end_ok else "failed"
        end_push_error = "" if end_ok else end_msg

    db.add(
        Notification(
            job_id=None,
            channel="discord",
            mode="digest",
            status="sent" if not send_errors else "failed",
            error="" if not send_errors else " | ".join(send_errors)[:2000],
        )
    )
    for item in selected_jobs:
        db.add(
            Notification(
                job_id=item["job_id"],
                channel="discord",
                mode="job_digest_item",
                status="sent" if not send_errors else "failed",
                error="" if not send_errors else "digest send failed",
            )
        )
    if end_push_status in {"sent", "failed"}:
        db.add(
            Notification(
                job_id=None,
                channel="discord",
                mode="end_of_push",
                status="sent" if end_push_sent else "failed",
                error=end_push_error[:2000],
            )
        )
    db.commit()

    return digest


def list_runs(db: Session, limit: int = 100) -> list[CrawlRun]:
    return db.query(CrawlRun).order_by(desc(CrawlRun.started_at)).limit(limit).all()
