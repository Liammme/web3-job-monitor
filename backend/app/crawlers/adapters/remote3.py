from __future__ import annotations
from app.crawlers.base import SourceAdapter


class Remote3Adapter(SourceAdapter):
    source_name = "remote3"

    def fetch(self):
        # The current listing page is category-oriented and does not provide stable
        # individual job cards for reliable company/job extraction. Return empty
        # results instead of ingesting noisy non-job links.
        return []
