from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.crawlers.base import NormalizedJob, SourceAdapter


def _to_remote_type(office_mode: str) -> str:
    text = (office_mode or "").strip().lower()
    if "remote" in text or "远程" in text:
        return "remote"
    return "unknown"


def _build_jobs(results: list[dict[str, Any]]) -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    for item in results:
        topic_id = item.get("topicId")
        title = str(item.get("positionName") or "").strip()
        company = str(item.get("company") or "").strip()
        if not title:
            continue

        canonical_url = str(item.get("url") or "").strip()
        if not canonical_url and topic_id:
            canonical_url = f"https://dejob.ai/jobDetail?id={topic_id}"

        created_ms = item.get("createTime")
        posted_at = None
        if isinstance(created_ms, (int, float)) and created_ms > 0:
            posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).replace(tzinfo=None)

        content = "\n".join(
            [
                str(item.get("content") or "").strip(),
                str(item.get("content2") or "").strip(),
                str(item.get("content3") or "").strip(),
            ]
        ).strip()

        jobs.append(
            NormalizedJob(
                source_job_id=str(topic_id) if topic_id is not None else canonical_url,
                canonical_url=canonical_url or "https://www.dejob.ai/job",
                title=title,
                company=company,
                location=str(item.get("location") or "").strip(),
                remote_type=_to_remote_type(str(item.get("officeModeName") or "")),
                employment_type=str(item.get("workTypeName") or "unknown").strip() or "unknown",
                description=content[:4000],
                posted_at=posted_at,
                raw_payload={
                    "site": "dejob",
                    "company_url": str(item.get("companyWebsite") or "").strip(),
                    "office_mode": str(item.get("officeModeName") or "").strip(),
                },
            )
        )
    return jobs


class DeJobAdapter(SourceAdapter):
    source_name = "dejob"

    def fetch(self) -> list[NormalizedJob]:
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"}
        all_results: list[dict[str, Any]] = []

        with httpx.Client(timeout=25, follow_redirects=True, headers=headers) as client:
            # Pull a bounded number of pages for stability and speed.
            for page in range(1, 5):
                url = f"https://dejob.ai/api/worker/topics?page={page}&limit=20"
                resp = client.get(url)
                resp.raise_for_status()
                payload = resp.json()
                data = payload.get("data") if isinstance(payload, dict) else {}
                results = data.get("results") if isinstance(data, dict) else []
                if not isinstance(results, list) or not results:
                    break
                all_results.extend(results)
                if len(results) < 20:
                    break

        return _build_jobs(all_results)[:80]
