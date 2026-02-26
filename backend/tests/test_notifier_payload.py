from __future__ import annotations
from app.services.notifier import DiscordNotifier


def test_single_payload_shape():
    payload = DiscordNotifier.build_single_payload(
        {
            "source_name": "web3career",
            "title": "Senior Solidity Engineer",
            "company": "Acme",
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
