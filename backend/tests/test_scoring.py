from __future__ import annotations
from app.services.scoring import Scorer
from app.services.seed import default_score_config


def test_score_boundary_69_70_71():
    scorer = Scorer(default_score_config())

    low = scorer.score({"title": "Blockchain Engineer", "description": "", "location": "", "remote_type": ""})
    assert low.total_score < 70
    assert low.decision == "low"

    exact = scorer.score(
        {
            "title": "Senior Solidity Smart Contract DeFi Engineer",
            "description": "remote global",
            "location": "global",
            "remote_type": "remote",
        }
    )
    assert exact.total_score >= 70
    assert exact.decision == "high"

    high = scorer.score(
        {
            "title": "Principal Rust Protocol Engineer",
            "description": "DeFi rollup remote global",
            "location": "global",
            "remote_type": "remote",
        }
    )
    assert high.total_score > exact.total_score
    assert high.decision == "high"


def test_scorer_merges_ai_keywords_for_legacy_config():
    legacy_cfg = {
        "strong_keywords": {
            "solidity": 12,
            "smart contract": 12,
            "protocol": 12,
            "defi": 12,
            "mev": 12,
            "rollup": 12,
            "zk": 12,
            "rust": 12,
            "evm": 12,
        },
        "medium_keywords": {
            "web3": 6,
            "crypto": 6,
            "blockchain": 6,
            "wallet": 6,
            "node": 6,
        },
        "strong_cap": 60,
        "medium_cap": 30,
        "seniority": default_score_config()["seniority"],
        "remote_bonus": 15,
        "global_bonus": 5,
        "threshold": 70,
        "reject_if_negative_and_below": 80,
        "negative_keywords": ["sales", "business development", "bd", "account executive"],
    }
    scorer = Scorer(legacy_cfg)
    result = scorer.score(
        {
            "title": "Software Engineer",
            "description": "Build retrieval augmented generation and large language model services.",
            "location": "",
            "remote_type": "",
        }
    )
    assert result.keyword_score > 0
    assert "large language model" in result.matched_keywords


def test_scorer_does_not_match_ai_inside_campaign():
    scorer = Scorer(default_score_config())
    result = scorer.score(
        {
            "title": "Growth Specialist",
            "description": "Own campaign lifecycle and demand generation.",
            "location": "",
            "remote_type": "",
        }
    )
    assert "ai" not in result.matched_keywords
