from __future__ import annotations
from datetime import datetime
import json

import httpx


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @staticmethod
    def build_single_payload(job: dict, score: dict, run_id: int) -> dict:
        posted_at = job.get("posted_at")
        if isinstance(posted_at, datetime):
            posted_text = posted_at.strftime("%Y-%m-%d %H:%M UTC")
        else:
            posted_text = str(posted_at or "N/A")

        job_title = " ".join(str(job.get("title") or "").splitlines()[0].split())
        if len(job_title) > 110:
            job_title = f"{job_title[:107]}..."

        desc = (
            f"**公司名:** {job.get('company') or 'N/A'}\n"
            f"**来源:** {job['source_name']}\n"
            f"**来源网站:** {job.get('source_website') or 'N/A'}\n"
            f"**公司网址:** {job.get('company_url') or 'N/A'}\n"
            f"**岗位发布时间:** {posted_text}\n"
            f"**地点:** {job.get('location') or 'N/A'}\n"
            f"**远程类型:** {job.get('remote_type') or 'N/A'}\n"
            f"**岗位评分:** {score['total_score']} ({score['decision']})\n"
            f"**评分计算:** 关键词 {score.get('keyword_score', 0)} + "
            f"级别 {score.get('seniority_score', 0)} + "
            f"远程 {score.get('remote_bonus', 0)} + "
            f"地区 {score.get('region_bonus', 0)}"
        )
        return {
            "embeds": [
                {
                    "title": f"[HIGH] {job_title}",
                    "description": desc,
                    "url": job["canonical_url"],
                }
            ]
        }

    @staticmethod
    def build_digest_payload(summary: dict) -> dict:
        lines = [
            "最近有招聘需求的公司（按最高评分排序）",
            "用于判断优先联系对象：状态 + 联系优先级 + 重点岗位",
            "",
        ]
        companies = summary.get("company_summaries", [])
        if not companies:
            lines.append("- 暂无新增公司")
        for item in companies:
            lines.append(
                f"- {item['company']}｜状态 {item['hiring_status']}｜联系优先级 {item['contact_priority']}｜{item['contact_action']}"
            )
            lines.append(
                f"  新增岗位 {item['new_jobs']}（近7天 {item['recent_7d']}｜近30天 {item['recent_30d']}）"
            )
            lines.append(f"  首次发现招聘：{item.get('first_seen_at') or 'N/A'}")
            lines.append(f"  公司网址：{item['company_url'] or 'N/A'}")
            lines.append(
                f"  来源网站（主要）：{item['main_source']} ({item.get('main_source_website') or 'N/A'})"
            )
            clues = item.get("contact_clues") or {}
            lines.append(
                f"  联系线索：邮箱 {clues.get('email', 'N/A')}｜Telegram {clues.get('telegram', 'N/A')}｜招聘页 {clues.get('career_url', 'N/A')}"
            )
            top_roles = item.get("top_roles", [])
            if top_roles:
                lines.append("  重点岗位：")
                for role in top_roles:
                    lines.append(
                        f"   - {role['title']}｜评分 {role['score']}｜发布时间 {role.get('posted_at', 'N/A')}｜{role.get('location', 'N/A')}｜{role.get('employment_type', 'N/A')}｜{role['url']}"
                    )

        lines.extend(
            [
                "",
                f"本轮新增岗位: **{summary['new_jobs']}**",
                f"高优先岗位: **{summary['high_priority_jobs']}**",
                f"抓取失败来源: **{', '.join(summary['failed_sources']) or 'none'}**",
            ]
        )

        high_jobs = summary.get("high_jobs", [])
        lines.append("")
        lines.append("高优先岗位明细（本轮）:")
        if not high_jobs:
            lines.append("- 无")
        else:
            for item in high_jobs:
                lines.append(
                    f"- {item['company']}｜{item['title']}｜评分 {item['score']}｜发布时间 {item.get('posted_at', 'N/A')}｜{item.get('location', 'N/A')}｜{item.get('employment_type', 'N/A')}｜来源 {item['source']}｜{item['url']}"
                )

        full_text = "\n".join(lines)
        # Discord content length limit is 2000. If the report is long, keep one
        # message and attach full text as a file so downstream bots can parse it.
        if len(full_text) <= 1900:
            return {"content": full_text}
        return {
            "content": "Web3 招聘监控汇总（完整版见附件 web3_digest.txt）",
            "_file_text": full_text,
            "_file_name": "web3_digest.txt",
        }

    def send(self, payload: dict) -> tuple[bool, str]:
        if not self.webhook_url:
            return False, "webhook not configured"
        try:
            file_text = payload.get("_file_text")
            file_name = payload.get("_file_name", "digest.txt")
            base_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
            with httpx.Client(timeout=20) as client:
                if isinstance(file_text, str) and file_text:
                    resp = client.post(
                        self.webhook_url,
                        data={"payload_json": json.dumps(base_payload, ensure_ascii=False)},
                        files={"file": (file_name, file_text.encode("utf-8"), "text/plain; charset=utf-8")},
                    )
                else:
                    resp = client.post(self.webhook_url, json=base_payload)
                if resp.status_code >= 300:
                    return False, f"discord status={resp.status_code} body={resp.text[:300]}"
            return True, "ok"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
