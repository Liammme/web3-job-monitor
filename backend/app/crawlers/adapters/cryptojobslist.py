from __future__ import annotations
from app.crawlers.adapters.common import scrape_jobs_from_listing
from app.crawlers.base import SourceAdapter


class CryptoJobsListAdapter(SourceAdapter):
    source_name = "cryptojobslist"

    def fetch(self):
        return scrape_jobs_from_listing(
            "https://cryptojobslist.com",
            "cryptojobslist",
            "cryptojobslist.com",
        )
