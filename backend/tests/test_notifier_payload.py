from __future__ import annotations
from app.services.notifier import DiscordNotifier


def test_single_payload_shape():
    payload = DiscordNotifier.build_single_payload(
        {
            "source_name": "web3career",
            "title": "Senior Solidity Engineer",
            "company": "Acme",
            "company_url": "https://acme.org",
            "source_website": "https://web3.career",
            "location": "global",
            "remote_type": "remote",
            "canonical_url": "https://web3.career/job/1",
        },
        {"total_score": 84, "decision": "high", "matched_keywords": ["solidity", "defi"]},
        run_id=9,
    )

    assert "embeds" in payload
    assert payload["embeds"][0]["title"].startswith("[HIGH]")
    assert "run_id=9" in payload["embeds"][0]["footer"]["text"]
    assert "公司网址" in payload["embeds"][0]["description"]


def test_digest_payload_company_section():
    payload = DiscordNotifier.build_digest_payload(
        {
            "new_jobs": 4,
            "high_priority_jobs": 1,
            "failed_sources": [],
            "source_stats": [
                {"source": "web3career", "fetched": 4, "new": 4, "high": 1, "status": "success"},
            ],
            "company_summaries": [
                {
                    "company": "B Corp",
                    "new_jobs": 2,
                    "max_score": 88.0,
                    "avg_score": 75.0,
                    "company_url": "https://b.example.com",
                    "main_source": "web3career",
                    "main_source_website": "https://web3.career",
                },
                {
                    "company": "A Corp",
                    "new_jobs": 2,
                    "max_score": 92.0,
                    "avg_score": 79.0,
                    "company_url": "https://a.example.com",
                    "main_source": "linkedin",
                    "main_source_website": "https://linkedin.com/jobs",
                },
            ],
        }
    )

    content = payload["content"]
    assert "最近有招聘需求的公司" in content
    assert "公司网址" in content
    assert "来源网站（主要）" in content
    # Notifier should output companies in provided order; sorting is verified in crawl_service test.
    assert content.index("B Corp") < content.index("A Corp")
