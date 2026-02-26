from __future__ import annotations
from app.crawlers.adapters.common import scrape_jobs_from_listing
from app.crawlers.base import SourceAdapter


class WellfoundAdapter(SourceAdapter):
    source_name = "wellfound"

    def fetch(self):
        return scrape_jobs_from_listing(
            "https://wellfound.com/role/l/web3",
            "wellfound",
            "wellfound.com",
        )
