from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


def _parse_datetime(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


class CryptocurrencyJobsAdapter(SourceAdapter):
    source_name = "cryptocurrencyjobs"

    def fetch(self) -> list[NormalizedJob]:
        listing_url = "https://www.cryptocurrencyjobs.co/"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for row in soup.select("#find-a-job ul.mt-6 > li.grid"):
            title_el = row.select_one("h2 a[href]")
            if not title_el:
                continue
            href = title_el.get("href", "")
            if not re.match(r"^/[a-z0-9-]+/[a-z0-9-]+/$", href):
                continue

            canonical_url = urljoin("https://www.cryptocurrencyjobs.co", href)
            if canonical_url in seen:
                continue

            title = " ".join(title_el.get_text(" ", strip=True).split())
            if not title:
                continue

            company = ""
            company_url = ""
            company_el = row.select_one("h3 a[href]")
            if company_el:
                company = " ".join(company_el.get_text(" ", strip=True).split())
                company_url = urljoin("https://www.cryptocurrencyjobs.co", company_el.get("href", ""))

            meta_texts = [" ".join(x.get_text(" ", strip=True).split()) for x in row.select("div.flex.flex-row.flex-wrap h4")]
            location = meta_texts[0] if len(meta_texts) >= 1 else ""
            employment_type = meta_texts[2] if len(meta_texts) >= 3 else "unknown"

            time_el = row.select_one("time[datetime]")
            posted_at = _parse_datetime(time_el.get("datetime", "")) if time_el else None

            tags = []
            for tag in row.select("ul.flex.flex-wrap a[href]"):
                text = " ".join(tag.get_text(" ", strip=True).split())
                if text:
                    tags.append(text)
            description = " ".join(tags[:12])[:4000]

            jobs.append(
                NormalizedJob(
                    source_job_id=href,
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=location,
                    remote_type="remote" if "remote" in location.lower() else "unknown",
                    employment_type=employment_type or "unknown",
                    description=description,
                    posted_at=posted_at,
                    raw_payload={"site": "cryptocurrencyjobs", "company_url": company_url},
                )
            )
            seen.add(canonical_url)

        return jobs[:80]
