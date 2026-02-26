from __future__ import annotations
from app.crawlers.adapters.common import scrape_jobs_from_listing
from app.crawlers.base import SourceAdapter


class Remote3Adapter(SourceAdapter):
    source_name = "remote3"

    def fetch(self):
        return scrape_jobs_from_listing(
            "https://www.remote3.co/remote-web3-jobs",
            "remote3",
            "remote3.co",
        )
