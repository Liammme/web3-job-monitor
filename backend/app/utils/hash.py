from __future__ import annotations
import hashlib


def job_fallback_hash(canonical_url: str, title: str, company: str) -> str:
    raw = f"{canonical_url.strip().lower()}|{title.strip().lower()}|{company.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
