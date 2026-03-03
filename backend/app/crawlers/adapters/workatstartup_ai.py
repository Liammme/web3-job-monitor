from __future__ import annotations

from datetime import datetime, timedelta
import html as html_lib
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

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

    match = re.search(
        r"(?:about\s+)?(\d+)\s*(hour|hours|day|days|week|weeks|month|months|min|mins|minute|minutes)",
        raw,
    )
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)
    if unit in {"min", "mins", "minute", "minutes"}:
        return now - timedelta(minutes=value)
    if unit in {"hour", "hours"}:
        return now - timedelta(hours=value)
    if unit in {"day", "days"}:
        return now - timedelta(days=value)
    if unit in {"week", "weeks"}:
        return now - timedelta(weeks=value)
    if unit in {"month", "months"}:
        return now - timedelta(days=value * 30)
    return None


class WorkAtStartupAIAdapter(SourceAdapter):
    source_name = "workatstartup_ai"

    @staticmethod
    def _extract_detail(detail_url: str) -> tuple[str, str, str]:
        try:
            html = fetch_html(detail_url, timeout=25)
        except Exception:
            return "", "", ""

        soup, _ = soup_links(html)
        company = ""
        company_url = ""
        description = ""

        data_node = soup.select_one("div[id^='WaasShowJobPage-react-component'][data-page]")
        if data_node:
            data_raw = data_node.get("data-page", "")
            if data_raw:
                try:
                    data = json.loads(html_lib.unescape(data_raw))
                except Exception:
                    data = {}
                props = data.get("props", {}) if isinstance(data, dict) else {}
                if isinstance(props, dict):
                    job_data = props.get("job", {}) if isinstance(props.get("job"), dict) else {}
                    company_data = props.get("company", {}) if isinstance(props.get("company"), dict) else {}

                    company_name = job_data.get("companyName") or company_data.get("name")
                    if isinstance(company_name, str):
                        company = " ".join(company_name.split()).strip()

                    website = company_data.get("website")
                    if isinstance(website, str) and website.startswith("http"):
                        company_url = website.strip()
                    else:
                        company_path = job_data.get("companyUrl")
                        if isinstance(company_path, str) and company_path:
                            company_url = urljoin("https://www.ycombinator.com", company_path)

                    desc_html = job_data.get("description")
                    if isinstance(desc_html, str) and desc_html:
                        description = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)

        if not description:
            meta_desc = soup.select_one("meta[property='og:description']")
            if meta_desc:
                fallback_desc = meta_desc.get("content", "")
                if isinstance(fallback_desc, str):
                    description = fallback_desc

        description = " ".join((description or "").split())[:4000]
        return company, company_url, description

    def fetch(self) -> list[NormalizedJob]:
        listing_url = "https://www.workatastartup.com/jobs?query=ai"
        html = fetch_html(listing_url)
        soup, _ = soup_links(html)

        jobs: list[NormalizedJob] = []
        seen: set[str] = set()

        for card in soup.select("div.jobs-list > div > div"):
            title_el = card.select_one("a[data-jobid][target='job'][href*='ycombinator.com/companies/']")
            if not title_el:
                continue

            canonical_url = title_el.get("href", "").strip()
            if not canonical_url or canonical_url in seen:
                continue

            title = " ".join(title_el.get_text(" ", strip=True).split())
            if not title:
                continue

            job_id = title_el.get("data-jobid", "").strip() or canonical_url

            company_el = card.select_one("div.company-details a > span.font-bold")
            company = " ".join(company_el.get_text(" ", strip=True).split()) if company_el else ""
            company = re.sub(r"\s*\([^)]*\)\s*$", "", company).strip()

            posted_raw = ""
            posted_hint = card.select_one("div.company-details a > span.text-gray-300")
            if posted_hint:
                posted_raw = " ".join(posted_hint.get_text(" ", strip=True).split()).strip("()")
            posted_at = _parse_relative_posted(posted_raw)

            detail_spans = [" ".join(x.get_text(" ", strip=True).split()) for x in card.select("p.job-details span")]
            employment_type = detail_spans[0] if len(detail_spans) >= 1 else "unknown"
            location = detail_spans[1] if len(detail_spans) >= 2 else ""

            description = ""
            desc_el = card.select_one("div.company-details a > span.text-gray-600")
            if desc_el:
                description = " ".join(desc_el.get_text(" ", strip=True).split())[:4000]

            company_url = ""
            company_link = card.select_one("a[target='company'][href]")
            if company_link:
                company_url = company_link.get("href", "").strip()

            detail_company, detail_company_url, detail_description = self._extract_detail(canonical_url)
            if detail_company:
                company = detail_company
            if detail_company_url:
                company_url = detail_company_url
            if detail_description:
                description = detail_description

            jobs.append(
                NormalizedJob(
                    source_job_id=job_id,
                    canonical_url=canonical_url,
                    title=title,
                    company=company,
                    location=location,
                    remote_type="remote" if "remote" in location.lower() else "unknown",
                    employment_type=employment_type or "unknown",
                    description=description,
                    posted_at=posted_at,
                    raw_payload={"site": "workatstartup_ai", "company_url": company_url},
                )
            )
            seen.add(canonical_url)

        return jobs[:80]
