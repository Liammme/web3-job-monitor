from __future__ import annotations
from datetime import datetime, timezone

import httpx


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @staticmethod
    def build_single_payload(job: dict, score: dict, run_id: int) -> dict:
        desc = (
            f"**Source:** {job['source_name']}\\n"
            f"**Location:** {job.get('location') or 'N/A'}\\n"
            f"**Remote:** {job.get('remote_type') or 'N/A'}\\n"
            f"**Score:** {score['total_score']} ({score['decision']})\\n"
            f"**Keywords:** {', '.join(score.get('matched_keywords', [])) or 'None'}"
        )
        return {
            "embeds": [
                {
                    "title": f"[HIGH] {job['title']} @ {job.get('company') or 'Unknown'}",
                    "description": desc,
                    "url": job["canonical_url"],
                    "footer": {"text": f"run_id={run_id} collected_at={datetime.now(timezone.utc).isoformat()}"},
                }
            ]
        }

    @staticmethod
    def build_digest_payload(summary: dict) -> dict:
        lines = [
            f"new_jobs: **{summary['new_jobs']}**",
            f"high_priority: **{summary['high_priority_jobs']}**",
            f"failed_sources: **{', '.join(summary['failed_sources']) or 'none'}**",
            "",
            "by_source:",
        ]
        for item in summary["source_stats"]:
            lines.append(
                f"- {item['source']}: fetched={item['fetched']} new={item['new']} high={item['high']} status={item['status']}"
            )
        return {"content": "\\n".join(lines)}

    def send(self, payload: dict) -> tuple[bool, str]:
        if not self.webhook_url:
            return False, "webhook not configured"
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.post(self.webhook_url, json=payload)
                if resp.status_code >= 300:
                    return False, f"discord status={resp.status_code} body={resp.text[:300]}"
            return True, "ok"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
