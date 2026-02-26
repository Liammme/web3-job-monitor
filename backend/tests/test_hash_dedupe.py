from __future__ import annotations
from app.utils.hash import job_fallback_hash


def test_fallback_hash_is_stable_and_case_insensitive():
    a = job_fallback_hash("https://x.com/job/1", "Senior Solidity Engineer", "Acme")
    b = job_fallback_hash(" https://x.com/job/1 ", "senior solidity engineer", "acme")
    c = job_fallback_hash("https://x.com/job/2", "senior solidity engineer", "acme")

    assert a == b
    assert a != c
