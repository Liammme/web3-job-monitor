from __future__ import annotations

from datetime import datetime, timedelta
import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


def _parse_relative_posted(text: str) -> datetime | None:
    raw = " ".join((text or "").split()).strip().lower()
    if not raw:
        return None

    now = datetime.utcnow()
    if raw in {"today", "just now", "now"}:
        return now
    if raw == "yesterday":
        return now - timedelta(days=1)

    match = re.search(r"(?:about\s+)?(\d+)\s*(h|hr|hrs|hour|hours|d|day|days|w|wk|wks|week|weeks)", raw)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)
    if unit in {"h", "hr", "hrs", "hour", "hours"}:
        return now - timedelta(hours=value)
    if unit in {"d", "day", "days"}:
        return now - timedelta(days=value)
    if unit in {"w", "wk", "wks", "week", "weeks"}:
        return now - timedelta(weeks=value)
    return None


class AIJobsNetAdapter(SourceAdapter):
    source_name = "aijobsnet"

    def fetch(self) -> list[NormalizedJob]:
        listing_url = "https://aijobs.net/"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for row in soup.select("ul#job_list > li"):
            title_el = row.select_one("a[href^='/job/']")
            if not title_el:
                continue

            href = title_el.get("href", "")
            canonical_url = urljoin("https://aijobs.net", href)
            if not href or canonical_url in seen:
                continue

            title = " ".join(title_el.get_text(" ", strip=True).split())
            if not title:
                continue

            posted_text_el = row.select_one("div.text-end .text-muted")
            posted_text = " ".join(posted_text_el.get_text(" ", strip=True).split()) if posted_text_el else ""
            posted_at = _parse_relative_posted(posted_text)

            location_el = row.select_one("div.text-end > div:nth-of-type(2)")
            location = " ".join(location_el.get_text(" ", strip=True).split()) if location_el else ""

            levels = [x.get_text(" ", strip=True) for x in row.select("div.text-end .text-bg-warning, div.text-end .text-bg-secondary")]
            employment_type = "unknown"
            for value in levels:
                lower = value.lower()
                if "full" in lower or "part" in lower or "contract" in lower or "intern" in lower:
                    employment_type = value
                    break

            chips = [x.get_text(" ", strip=True) for x in row.select("div > div > span")]
            description = " | ".join([x for x in chips if x])[:4000]

            jobs.append(
                NormalizedJob(
                    source_job_id=href.strip("/"),
                    canonical_url=canonical_url,
                    title=title,
                    company="",
                    location=location,
                    remote_type="remote" if "remote" in location.lower() else "unknown",
                    employment_type=employment_type,
                    description=description,
                    posted_at=posted_at,
                    raw_payload={"site": "aijobsnet"},
                )
            )
            seen.add(canonical_url)

        return jobs[:80]
