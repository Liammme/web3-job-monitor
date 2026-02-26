from __future__ import annotations
from collections import defaultdict
from datetime import datetime

import httpx


class DiscordNotifier:
    MAX_DETAILED_COMPANIES = 20
    MIN_DETAILED_PER_SOURCE = 2

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
    def _split_companies_for_digest(cls, companies: list[dict]) -> tuple[list[dict], list[dict]]:
        if len(companies) <= cls.MAX_DETAILED_COMPANIES:
            return companies, []

        source_to_indexes: dict[str, list[int]] = defaultdict(list)
        source_order: list[str] = []
        for idx, item in enumerate(companies):
            source = str(item.get("main_source") or "unknown")
            if source not in source_to_indexes:
                source_order.append(source)
            source_to_indexes[source].append(idx)

        selected: set[int] = set()
        cursors = {source: 0 for source in source_order}

        for _ in range(cls.MIN_DETAILED_PER_SOURCE):
            for source in source_order:
                if len(selected) >= cls.MAX_DETAILED_COMPANIES:
                    break
                cursor = cursors[source]
                indexes = source_to_indexes[source]
                if cursor < len(indexes):
                    selected.add(indexes[cursor])
                    cursors[source] = cursor + 1

        for idx in range(len(companies)):
            if len(selected) >= cls.MAX_DETAILED_COMPANIES:
                break
            selected.add(idx)

        detailed_indexes = sorted(selected)
        detailed_companies = [companies[i] for i in detailed_indexes]
        overflow_companies = [item for i, item in enumerate(companies) if i not in selected]
        return detailed_companies, overflow_companies

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
            "时间窗口: 仅统计最近24小时内发布岗位",
            f"每日岗位推送上限: {summary.get('daily_job_push_limit', 50)}",
            f"过去24小时已推送: {summary.get('sent_last_24h', 0)}",
            f"本轮可推送名额: {summary.get('remaining_quota', 0)}",
            f"本轮候选岗位: {summary.get('candidate_jobs', 0)}",
            f"本轮实际推送岗位: {summary.get('selected_jobs_count', 0)}",
            f"超上限未推送: {summary.get('deferred_jobs_count', 0)}",
            f"新增岗位: {summary.get('new_jobs', 0)}",
            f"高优先岗位: {summary.get('high_priority_jobs', 0)}",
            f"失败来源: {failed_sources}",
            "",
            *source_lines,
        ]
        selected_source_stats = summary.get("selected_source_stats") or {}
        if selected_source_stats:
            overview_lines.extend(
                [
                    "",
                    "本轮已推送岗位来源分布：",
                    *[f"- {src}: {count}" for src, count in sorted(selected_source_stats.items(), key=lambda x: (-x[1], x[0]))],
                ]
            )
        payloads.append({"content": "\n".join(overview_lines)})

        selected_jobs = summary.get("selected_jobs") or []
        if selected_jobs:
            job_lines = ["本轮岗位推送（按评分+级别排序）:"]
            for idx, item in enumerate(selected_jobs, start=1):
                job_lines.append(
                    f"{idx}. {item['company']} | {item['title']} | 评分 {item['score']:.1f} | 级别分 {item.get('seniority_score', 0):.1f} | 来源 {item['source']} | 发布时间 {item.get('posted_at', 'N/A')}"
                )
                job_lines.append(f"   岗位链接: {item['url']}")
            for chunk in cls._split_lines(job_lines):
                payloads.append({"content": chunk})
        else:
            payloads.append({"content": "本轮岗位推送: 无（名额已用完或无新增岗位）"})

        deferred_jobs = summary.get("deferred_jobs") or []
        if deferred_jobs:
            deferred_lines = [f"超上限未推送岗位（公司+岗位名，展示前 {len(deferred_jobs)} 条）:"]
            for item in deferred_jobs:
                deferred_lines.append(f"- {item['company']} | {item['title']}")
            for chunk in cls._split_lines(deferred_lines):
                payloads.append({"content": chunk})

        # Backward-compatible fallback for older payload shape.
        if summary.get("selected_jobs") is not None:
            return payloads

        companies = summary.get("company_summaries", [])
        if not companies:
            payloads.append({"content": "最近有招聘需求的公司：暂无新增公司"})
        else:
            detailed_companies, overflow_companies = cls._split_companies_for_digest(companies)

            for idx, item in enumerate(detailed_companies, start=1):
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

            if overflow_companies:
                overflow_lines = [
                    f"其余公司（仅公司+岗位名，共 {len(overflow_companies)} 家）:",
                ]
                for item in overflow_companies:
                    titles = [x for x in (item.get("job_titles") or []) if isinstance(x, str) and x.strip()]
                    if not titles:
                        titles = [role.get("title") for role in (item.get("top_roles") or []) if role.get("title")]
                    title_text = " / ".join(titles[:3]) if titles else "N/A"
                    overflow_lines.append(f"- {item['company']} | {title_text}")
                for chunk in cls._split_lines(overflow_lines):
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
