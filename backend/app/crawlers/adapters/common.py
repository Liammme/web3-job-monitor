from __future__ import annotations
from urllib.parse import urljoin, urlparse

from app.crawlers.base import NormalizedJob
from app.crawlers.http_helpers import fetch_html, soup_links


KEYWORDS = ["job", "career", "position", "opening", "web3", "crypto", "blockchain"]


def scrape_jobs_from_listing(listing_url: str, site_name: str, host_contains: str) -> list[NormalizedJob]:
    html = fetch_html(listing_url)
    soup, links = soup_links(html)
    jobs: list[NormalizedJob] = []
    seen: set[str] = set()

    for a in links:
        href = (a.get("href") or "").strip()
        text = " ".join(a.get_text(" ", strip=True).split())
        if not href or not text:
            continue

        full_url = urljoin(listing_url, href)
        host = (urlparse(full_url).netloc or "").lower()
        if host_contains not in host:
            continue

        lower = f"{text} {full_url}".lower()
        if not any(k in lower for k in KEYWORDS):
            continue
        if len(text) < 8:
            continue
        if full_url in seen:
            continue
        seen.add(full_url)

        jobs.append(
            NormalizedJob(
                source_job_id=full_url,
                canonical_url=full_url,
                title=text[:220],
                company="",
                location="global",
                remote_type="unknown",
                employment_type="unknown",
                description="",
                raw_payload={"site": site_name, "from_listing": listing_url, "anchor_text": text},
            )
        )

    # Fallback: if no candidate link was captured, expose page title as synthetic job.
    if not jobs and soup.title and soup.title.text:
        jobs.append(
            NormalizedJob(
                source_job_id=listing_url,
                canonical_url=listing_url,
                title=soup.title.text.strip()[:220],
                company="",
                location="global",
                remote_type="unknown",
                employment_type="unknown",
                description="",
                raw_payload={"site": site_name, "fallback": True},
            )
        )

    return jobs[:80]
