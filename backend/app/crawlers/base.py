from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedJob:
    source_job_id: str | None
    canonical_url: str
    title: str
    company: str = ""
    location: str = ""
    remote_type: str = "unknown"
    employment_type: str = "unknown"
    description: str = ""
    posted_at: datetime | None = None
    raw_payload: dict = field(default_factory=dict)


class SourceAdapter:
    source_name: str

    def fetch(self) -> list[NormalizedJob]:
        raise NotImplementedError
