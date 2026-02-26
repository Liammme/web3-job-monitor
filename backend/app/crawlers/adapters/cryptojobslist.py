from __future__ import annotations

from datetime import datetime, timedelta
import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob
from app.crawlers.http_helpers import fetch_html, soup_links
from app.crawlers.base import SourceAdapter


class CryptoJobsListAdapter(SourceAdapter):
    source_name = "cryptojobslist"

    @staticmethod
    def _parse_posted_at(age_text: str) -> datetime | None:
        text = (age_text or "").strip().lower()
        if not text:
            return None
        now = datetime.utcnow()
        if text in {"now", "just now", "new"}:
            return now

        match = re.search(r"(\d+)\s*(m|min|mins|h|hr|hrs|d|day|days|w|wk|wks|mo|month|months)", text)
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2)
        if unit in {"m", "min", "mins"}:
            return now - timedelta(minutes=value)
        if unit in {"h", "hr", "hrs"}:
            return now - timedelta(hours=value)
        if unit in {"d", "day", "days"}:
            return now - timedelta(days=value)
        if unit in {"w", "wk", "wks"}:
            return now - timedelta(weeks=value)
        if unit in {"mo", "month", "months"}:
            return now - timedelta(days=value * 30)
        return None

    def fetch(self):
        listing_url = "https://cryptojobslist.com"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        rows = soup.select("table.job-preview-inline-table tbody tr")
        for row in rows:
            job_link_el = row.select_one("a[href^='/jobs/']")
            if not job_link_el:
                continue

            href = job_link_el.get("href", "")
            canonical_url = urljoin("https://cryptojobslist.com", href)
            if not href or canonical_url in seen:
                continue

            tds = row.find_all("td")
            title = " ".join(job_link_el.get_text(" ", strip=True).split())
            company = ""
            location = ""
            company_url = ""

            if len(tds) > 1:
                company = " ".join(tds[1].get_text(" ", strip=True).split())
                company_anchor = tds[1].find("a", href=True)
                if company_anchor:
                    company_url = urljoin("https://cryptojobslist.com", company_anchor["href"])
            if len(tds) > 3:
                location = " ".join(tds[3].get_text(" ", strip=True).split()).replace("📍", "").strip()
            age_text = ""
            if len(tds) > 6:
                age_text = " ".join(tds[6].get_text(" ", strip=True).split())
            posted_at = self._parse_posted_at(age_text)

            if not title:
                continue

            jobs.append(
                NormalizedJob(
                    source_job_id=href,
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=location,
                    remote_type="remote" if "remote" in location.lower() else "unknown",
                    employment_type="unknown",
                    description="",
                    posted_at=posted_at,
                    raw_payload={"site": "cryptojobslist", "company_url": company_url},
                )
            )
            seen.add(canonical_url)

        return jobs[:80]
