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
