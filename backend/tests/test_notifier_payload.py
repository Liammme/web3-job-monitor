from __future__ import annotations
from datetime import datetime

from app.services.notifier import DiscordNotifier


def test_single_payload_shape():
    payload = DiscordNotifier.build_single_payload(
        {
            "source_name": "web3career",
            "title": "Senior Solidity Engineer",
            "company": "Acme",
            "company_url": "https://acme.org",
            "source_website": "https://web3.career",
            "posted_at": datetime(2026, 2, 26, 8, 49, 4),
            "location": "global",
            "remote_type": "remote",
            "canonical_url": "https://web3.career/job/1",
        },
        {
            "total_score": 84,
            "decision": "high",
            "keyword_score": 48,
            "seniority_score": 20,
            "remote_bonus": 10,
            "region_bonus": 6,
        },
        run_id=9,
    )

    assert "embeds" in payload
    assert payload["embeds"][0]["title"].startswith("[HIGH]")
    assert "公司网址" in payload["embeds"][0]["description"]
    assert "公司名" in payload["embeds"][0]["description"]
    assert "岗位发布时间" in payload["embeds"][0]["description"]
    assert "评分计算" in payload["embeds"][0]["description"]
    assert "命中关键词" not in payload["embeds"][0]["description"]
    assert "footer" not in payload["embeds"][0]


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
                    "hiring_status": "扩招",
                    "contact_priority": 85,
                    "new_jobs": 2,
                    "recent_7d": 6,
                    "recent_30d": 20,
                    "max_score": 88.0,
                    "avg_score": 75.0,
                    "company_url": "https://b.example.com",
                    "main_source": "web3career",
                    "main_source_website": "https://web3.career",
                    "top_roles": [
                        {"title": "Senior Solidity Engineer", "score": 92.0, "url": "https://x/jobs/1"},
                    ],
                },
                {
                    "company": "A Corp",
                    "hiring_status": "新开招",
                    "contact_priority": 72,
                    "new_jobs": 2,
                    "recent_7d": 2,
                    "recent_30d": 2,
                    "max_score": 92.0,
                    "avg_score": 79.0,
                    "company_url": "https://a.example.com",
                    "main_source": "linkedin",
                    "main_source_website": "https://linkedin.com/jobs",
                    "top_roles": [],
                },
            ],
        }
    )

    content = payload["content"]
    assert "最近有招聘需求的公司" in content
    assert "公司网址" in content
    assert "来源网站（主要）" in content
    assert "联系优先级" in content
    assert "重点岗位" in content
    # Notifier should output companies in provided order; sorting is verified in crawl_service test.
    assert content.index("B Corp") < content.index("A Corp")
