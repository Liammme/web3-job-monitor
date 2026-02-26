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
            "high_jobs": [
                {
                    "company": "A Corp",
                    "title": "Senior Protocol Engineer",
                    "score": 92.0,
                    "posted_at": "2026-02-26",
                    "location": "Remote",
                    "employment_type": "FULL_TIME",
                    "source": "linkedin",
                    "url": "https://x/jobs/high-1",
                }
            ],
            "company_summaries": [
                {
                    "company": "B Corp",
                    "hiring_status": "扩招",
                    "contact_priority": 85,
                    "contact_action": "建议立即联系",
                    "new_jobs": 2,
                    "recent_7d": 6,
                    "recent_30d": 20,
                    "first_seen_at": "2026-02-01",
                    "max_score": 88.0,
                    "avg_score": 75.0,
                    "company_url": "https://b.example.com",
                    "main_source": "web3career",
                    "main_source_website": "https://web3.career",
                    "contact_clues": {
                        "email": "hr@b.example.com",
                        "telegram": "@bhrteam",
                        "career_url": "https://b.example.com/jobs",
                    },
                    "top_roles": [
                        {
                            "title": "Senior Solidity Engineer",
                            "score": 92.0,
                            "url": "https://x/jobs/1",
                            "posted_at": "2026-02-26",
                            "location": "Remote",
                            "employment_type": "FULL_TIME",
                        },
                    ],
                },
                {
                    "company": "A Corp",
                    "hiring_status": "新开招",
                    "contact_priority": 72,
                    "contact_action": "建议本周联系",
                    "new_jobs": 2,
                    "recent_7d": 2,
                    "recent_30d": 2,
                    "first_seen_at": "2026-02-26",
                    "max_score": 92.0,
                    "avg_score": 79.0,
                    "company_url": "https://a.example.com",
                    "main_source": "linkedin",
                    "main_source_website": "https://linkedin.com/jobs",
                    "contact_clues": {
                        "email": "N/A",
                        "telegram": "N/A",
                        "career_url": "https://a.example.com/jobs",
                    },
                    "top_roles": [],
                },
            ],
        }
    )

    assert isinstance(payload.get("content"), str)
    content = payload.get("_file_text", payload["content"])
    assert "最近有招聘需求的公司" in content
    assert "公司网址" in content
    assert "来源网站（主要）" in content
    assert "联系优先级" in content
    assert "重点岗位" in content
    assert "联系线索" in content
    assert "首次发现招聘" in content
    assert "高优先岗位明细（本轮）" in content
    assert content.index("B Corp") < content.index("A Corp")


def test_digest_payload_attaches_file_when_too_long():
    summary = {
        "new_jobs": 1,
        "high_priority_jobs": 0,
        "failed_sources": [],
        "source_stats": [],
        "high_jobs": [],
        "company_summaries": [
            {
                "company": f"Company{i}",
                "hiring_status": "持续招",
                "contact_priority": 50,
                "contact_action": "建议本周联系",
                "new_jobs": 1,
                "recent_7d": 1,
                "recent_30d": 2,
                "first_seen_at": "2026-02-26",
                "max_score": 88.0,
                "avg_score": 75.0,
                "company_url": "https://example.com",
                "main_source": "dejob",
                "main_source_website": "https://www.dejob.ai/job",
                "contact_clues": {"email": "N/A", "telegram": "N/A", "career_url": "https://example.com/jobs"},
                "top_roles": [
                    {
                        "title": "Very Long Role Name For Stress Test",
                        "score": 80.0,
                        "url": "https://example.com/jobs/1",
                        "posted_at": "2026-02-26",
                        "location": "Remote",
                        "employment_type": "FULL_TIME",
                    }
                ],
            }
            for i in range(50)
        ],
    }
    payload = DiscordNotifier.build_digest_payload(summary)
    assert "_file_text" in payload
    assert payload["_file_name"] == "web3_digest.txt"
