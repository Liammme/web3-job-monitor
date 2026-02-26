from __future__ import annotations
from datetime import datetime

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
    def _split_lines(lines: list[str], max_len: int = 1900) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for raw_line in lines:
            line = raw_line
            if len(line) > max_len:
                line = f"{line[: max_len - 3]}..."

            extra_len = len(line) if not current else len(line) + 1
            if current and (current_len + extra_len > max_len):
                chunks.append("\n".join(current))
                current = [line]
                current_len = len(line)
            else:
                current.append(line)
                current_len += extra_len

        if current:
            chunks.append("\n".join(current))
        return chunks

    @classmethod
    def build_digest_payloads(cls, summary: dict) -> list[dict]:
        payloads: list[dict] = []

        failed_sources = ", ".join(summary.get("failed_sources") or []) or "none"
        source_lines = ["来源执行情况："]
        for item in summary.get("source_stats", []):
            source_lines.append(
                f"- {item['source']}: fetched={item['fetched']} new={item['new']} high={item['high']} status={item['status']}"
            )

        overview_lines = [
            "Web3 招聘监控汇总",
            f"新增岗位: {summary.get('new_jobs', 0)}",
            f"高优先岗位: {summary.get('high_priority_jobs', 0)}",
            f"失败来源: {failed_sources}",
            "",
            *source_lines,
        ]
        payloads.append({"content": "\n".join(overview_lines)})

        companies = summary.get("company_summaries", [])
        if not companies:
            payloads.append({"content": "最近有招聘需求的公司：暂无新增公司"})
        else:
            for idx, item in enumerate(companies, start=1):
                company_lines = [
                    f"公司 {idx}: {item['company']}",
                    f"招聘状态: {item['hiring_status']}",
                    f"联系优先级: {item['contact_priority']}",
                    f"建议动作: {item['contact_action']}",
                    f"新增岗位: {item['new_jobs']} (近7天 {item['recent_7d']} | 近30天 {item['recent_30d']})",
                    f"首次发现招聘: {item.get('first_seen_at') or 'N/A'}",
                    f"公司网址: {item.get('company_url') or 'N/A'}",
                    f"主要来源: {item.get('main_source') or 'N/A'} ({item.get('main_source_website') or 'N/A'})",
                ]

                clues = item.get("contact_clues") or {}
                company_lines.append(
                    f"联系线索: 邮箱 {clues.get('email', 'N/A')} | Telegram {clues.get('telegram', 'N/A')} | 招聘页 {clues.get('career_url', 'N/A')}"
                )

                top_roles = item.get("top_roles", [])
                if top_roles:
                    company_lines.append("重点岗位:")
                    for role in top_roles:
                        company_lines.append(
                            f"- {role['title']} | 评分 {role['score']} | 发布时间 {role.get('posted_at', 'N/A')} | {role.get('location', 'N/A')} | {role.get('employment_type', 'N/A')}"
                        )
                        company_lines.append(f"  岗位链接: {role['url']}")
                else:
                    company_lines.append("重点岗位: N/A")

                for chunk in cls._split_lines(company_lines):
                    payloads.append({"content": chunk})

        high_jobs = summary.get("high_jobs", [])
        if high_jobs:
            detail_lines = ["高优先岗位明细（按评分排序）:"]
            for item in high_jobs:
                detail_lines.append(
                    f"- {item['company']} | {item['title']} | 评分 {item['score']} | 发布时间 {item.get('posted_at', 'N/A')} | {item.get('location', 'N/A')} | {item.get('employment_type', 'N/A')} | 来源 {item['source']}"
                )
                detail_lines.append(f"  岗位链接: {item['url']}")
            for chunk in cls._split_lines(detail_lines):
                payloads.append({"content": chunk})

        return payloads

    @classmethod
    def build_digest_payload(cls, summary: dict) -> dict:
        payloads = cls.build_digest_payloads(summary)
        if payloads:
            return payloads[0]
        return {"content": "Web3 招聘监控汇总: 无数据"}

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
