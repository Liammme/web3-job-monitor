from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urljoin

from app.crawlers.base import NormalizedJob, SourceAdapter
from app.crawlers.http_helpers import fetch_html, soup_links


def _parse_date(text: str) -> datetime | None:
    raw = " ".join((text or "").split()).strip()
    if not raw:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


class Web3JobsAiAdapter(SourceAdapter):
    source_name = "web3jobsai"

    @staticmethod
    def _extract_detail(detail_url: str) -> tuple[str, str, str]:
        try:
            html = fetch_html(detail_url, timeout=25)
            soup, _ = soup_links(html)
        except Exception:  # noqa: BLE001
            return "", "", ""

        company = ""
        company_url = ""
        company_el = soup.select_one("h3.employer-title a[href]")
        if company_el:
            company = " ".join(company_el.get_text(" ", strip=True).split())
            company_url = urljoin("https://web3jobs.ai", company_el.get("href", ""))

        desc_el = soup.select_one(".inner-job-description")
        description = " ".join(desc_el.get_text(" ", strip=True).split())[:4000] if desc_el else ""
        return company, company_url, description

    def fetch(self) -> list[NormalizedJob]:
        listing_url = "https://web3jobs.ai/jobs/"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()
        now = datetime.utcnow()

        for article in soup.select("article.job-list"):
            title_el = article.select_one("h2.job-title a[href*='/job/']")
            if not title_el:
                continue

            href = title_el.get("href", "")
            canonical_url = urljoin("https://web3jobs.ai", href)
            if not canonical_url or canonical_url in seen:
                continue

            title = " ".join(title_el.get_text(" ", strip=True).split())
            if not title:
                continue

            source_job_id = (article.get("id") or "").replace("post-", "").strip() or canonical_url
            location_el = article.select_one(".job-location")
            location = " ".join(location_el.get_text(" ", strip=True).split()) if location_el else ""

            employment_el = article.select_one(".job-type .type-job")
            employment = " ".join(employment_el.get_text(" ", strip=True).split()) if employment_el else "unknown"

            posted_el = article.select_one(".job-deadline.with-icon")
            posted_text = " ".join(posted_el.get_text(" ", strip=True).split()) if posted_el else ""
            posted_at = _parse_date(posted_text)

            company = ""
            company_url = ""
            description = ""
            # Only request detail pages for potentially recent roles to control runtime.
            if posted_at and posted_at >= now - timedelta(days=2):
                company, company_url, description = self._extract_detail(canonical_url)

            category_el = article.select_one(".category-job a")
            category = " ".join(category_el.get_text(" ", strip=True).split()) if category_el else ""
            if not description and category:
                description = f"category: {category}"

            jobs.append(
                NormalizedJob(
                    source_job_id=source_job_id,
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=location,
                    remote_type="remote" if "remote" in location.lower() else "unknown",
                    employment_type=employment or "unknown",
                    description=description,
                    posted_at=posted_at,
                    raw_payload={
                        "site": "web3jobsai",
                        "company_url": company_url,
                        "category": category,
                    },
                )
            )
            seen.add(canonical_url)

        return jobs[:80]
