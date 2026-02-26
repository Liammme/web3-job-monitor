from __future__ import annotations
from app.crawlers.adapters.common import scrape_jobs_from_listing
from app.crawlers.base import SourceAdapter


class LinkedInAdapter(SourceAdapter):
    source_name = "linkedin"

    def fetch(self):
        return scrape_jobs_from_listing(
            "https://www.linkedin.com/jobs/search/?keywords=web3%20crypto%20blockchain",
            "linkedin",
            "linkedin.com",
        )
