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
    payloads = DiscordNotifier.build_digest_payloads(
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
                    "job_titles": ["Senior Solidity Engineer"],
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
                    "job_titles": ["Product Manager"],
                },
            ],
        }
    )

    assert payloads
    assert all(isinstance(item.get("content"), str) for item in payloads)
    content = "\n".join(item["content"] for item in payloads)
    assert "Web3 招聘监控汇总" in content
    assert "公司网址" in content
    assert "主要来源" in content
    assert "联系优先级" in content
    assert "重点岗位" in content
    assert "联系线索" in content
    assert "首次发现招聘" in content
    assert content.index("B Corp") < content.index("A Corp")


def test_digest_payload_splits_when_too_long():
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
                "job_titles": ["Very Long Role Name For Stress Test"],
            }
            for i in range(50)
        ],
    }
    payloads = DiscordNotifier.build_digest_payloads(summary)
    assert len(payloads) > 2
    assert all(len(item["content"]) <= 1900 for item in payloads)
    content = "\n".join(item["content"] for item in payloads)
    assert "其余公司（仅公司+岗位名" in content


def test_digest_payload_balances_detailed_companies_by_source():
    def make_company(i: int, source: str) -> dict:
        return {
            "company": f"Company{i}",
            "hiring_status": "持续招",
            "contact_priority": 50,
            "contact_action": "建议本周联系",
            "new_jobs": 1,
            "recent_7d": 1,
            "recent_30d": 1,
            "first_seen_at": "2026-02-26",
            "max_score": 80.0 - i * 0.1,
            "avg_score": 70.0,
            "company_url": "https://example.com",
            "main_source": source,
            "main_source_website": f"https://{source}.example.com",
            "contact_clues": {"email": "N/A", "telegram": "N/A", "career_url": "https://example.com/jobs"},
            "top_roles": [],
            "job_titles": [f"Role{i}"],
        }

    companies = [make_company(i, "linkedin") for i in range(20)]
    companies.append(make_company(20, "dejob"))
    companies.append(make_company(21, "web3career"))

    payloads = DiscordNotifier.build_digest_payloads(
        {
            "new_jobs": 22,
            "high_priority_jobs": 0,
            "failed_sources": [],
            "source_stats": [],
            "high_jobs": [],
            "company_summaries": companies,
        }
    )

    content = "\n".join(item["content"] for item in payloads)
    assert "主要来源: dejob (https://dejob.example.com)" in content
    assert "主要来源: web3career (https://web3career.example.com)" in content


def test_digest_payload_uses_selected_jobs_section_when_present():
    payloads = DiscordNotifier.build_digest_payloads(
        {
            "new_jobs": 3,
            "high_priority_jobs": 2,
            "failed_sources": [],
            "source_stats": [],
            "daily_job_push_limit": 50,
            "sent_last_24h": 10,
            "remaining_quota": 40,
            "candidate_jobs": 3,
            "selected_jobs_count": 2,
            "deferred_jobs_count": 1,
            "selected_source_stats": {"web3career": 1, "dejob": 1},
            "selected_jobs": [
                {
                    "job_id": 1,
                    "company": "Acme",
                    "title": "Senior Solidity Engineer",
                    "score": 92.0,
                    "seniority_score": 20.0,
                    "source": "web3career",
                    "url": "https://example.com/1",
                    "posted_at": "2026-02-26 08:00 UTC",
                },
                {
                    "job_id": 2,
                    "company": "Beta",
                    "title": "Protocol Engineer",
                    "score": 88.0,
                    "seniority_score": 10.0,
                    "source": "dejob",
                    "url": "https://example.com/2",
                    "posted_at": "2026-02-26 07:00 UTC",
                },
            ],
            "deferred_jobs": [{"company": "Gamma", "title": "Backend Engineer"}],
        }
    )
    content = "\n".join(item["content"] for item in payloads)
    assert "每日岗位推送上限: 50" in content
    assert "本轮岗位推送（按评分+级别排序）" in content
    assert "Acme | Senior Solidity Engineer | 评分 92.0" in content
    assert "超上限未推送岗位（公司+岗位名" in content
