from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from app.crawlers.base import NormalizedJob
from app.crawlers.http_helpers import fetch_html, soup_links
from app.crawlers.base import SourceAdapter


class LinkedInAdapter(SourceAdapter):
    source_name = "linkedin"

    def fetch(self):
        listing_url = "https://www.linkedin.com/jobs/search/?keywords=web3%20crypto%20blockchain"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        cards = soup.select("div.base-card, div.base-search-card")
        for card in cards:
            title_el = card.select_one("h3.base-search-card__title") or card.select_one("h3")
            company_el = card.select_one("h4.base-search-card__subtitle a") or card.select_one(
                "h4.base-search-card__subtitle"
            )
            location_el = card.select_one(".job-search-card__location")
            job_link_el = card.select_one("a.base-card__full-link[href*='/jobs/view/']")

            if not title_el or not job_link_el:
                continue

            title = " ".join(title_el.get_text(" ", strip=True).split())
            company = ""
            company_url = ""
            if company_el:
                company = " ".join(company_el.get_text(" ", strip=True).split())
                if company_el.name == "a":
                    company_url = urljoin("https://www.linkedin.com", company_el.get("href", ""))

            job_url = urljoin("https://www.linkedin.com", job_link_el.get("href", ""))
            if not job_url or job_url in seen:
                continue

            # Keep canonical job link stable for dedupe.
            parsed = urlsplit(job_url)
            canonical_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

            job_id = None
            match = re.search(r"/jobs/view/.*-(\d+)", parsed.path)
            if match:
                job_id = match.group(1)

            jobs.append(
                NormalizedJob(
                    source_job_id=job_id or canonical_url,
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=" ".join(location_el.get_text(" ", strip=True).split()) if location_el else "",
                    remote_type="unknown",
                    employment_type="unknown",
                    description="",
                    raw_payload={"site": "linkedin", "company_url": company_url},
                )
            )
            seen.add(job_url)

        return jobs[:80]
