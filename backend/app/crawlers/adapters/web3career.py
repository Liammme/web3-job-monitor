from __future__ import annotations
from app.crawlers.adapters.common import scrape_jobs_from_listing
from app.crawlers.base import SourceAdapter


class Web3CareerAdapter(SourceAdapter):
    source_name = "web3career"

    def fetch(self):
        return scrape_jobs_from_listing(
            "https://web3.career/",
            "web3career",
            "web3.career",
        )
