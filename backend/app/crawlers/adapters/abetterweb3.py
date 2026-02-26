from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from typing import Any

import httpx

from app.crawlers.base import NormalizedJob, SourceAdapter


PAGE_ID = "daa09583-0b62-4e96-af46-de63fb9771b9"
NOTION_API_BASE = "https://www.notion.so/api/v3"


def _rich_text_to_str(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for chunk in value:
        if isinstance(chunk, list) and chunk:
            parts.append(str(chunk[0]))
    return unescape("".join(parts)).strip()


def _extract_collection_and_view(record_map: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    collections = record_map.get("collection") or {}
    collection_views = record_map.get("collection_view") or {}

    target_collection_id = ""
    target_schema: dict[str, Any] = {}
    for cid, wrapped in collections.items():
        value = (wrapped or {}).get("value") or {}
        schema = value.get("schema") or {}
        names = {str((meta or {}).get("name") or "") for meta in schema.values()}
        if "项目/公司" in names and "岗位需求" in names:
            target_collection_id = cid
            target_schema = schema
            break

    if not target_collection_id and collections:
        target_collection_id, wrapped = next(iter(collections.items()))
        target_schema = ((wrapped or {}).get("value") or {}).get("schema") or {}

    if not target_collection_id:
        raise ValueError("cannot locate target collection")

    target_view_id = ""
    for vid, wrapped in collection_views.items():
        value = (wrapped or {}).get("value") or {}
        source_collection = value.get("source_collection_id") or (
            (value.get("format") or {}).get("collection_pointer") or {}
        ).get("id")
        if source_collection == target_collection_id and value.get("type") == "table":
            target_view_id = vid
            if value.get("name") == "最近编辑":
                break

    if not target_view_id:
        raise ValueError("cannot locate target collection view")

    return target_collection_id, target_view_id, target_schema


def _build_jobs_from_blocks(blocks: dict[str, Any], collection_id: str, schema: dict[str, Any]) -> list[NormalizedJob]:
    key_to_name = {key: str((meta or {}).get("name") or "") for key, meta in schema.items()}

    jobs: list[NormalizedJob] = []
    for bid, wrapped in blocks.items():
        value = (wrapped or {}).get("value") or {}
        if value.get("type") != "page":
            continue
        if value.get("parent_table") != "collection" or value.get("parent_id") != collection_id:
            continue

        props = value.get("properties") or {}
        named_props: dict[str, str] = {}
        for prop_key, prop_value in props.items():
            name = key_to_name.get(prop_key, prop_key)
            named_props[name] = _rich_text_to_str(prop_value)

        company = named_props.get("项目/公司", "").strip()
        job_need = named_props.get("岗位需求", "").strip()
        title = job_need or (f"{company} 招聘" if company else "")
        if not title:
            continue

        apply_url = (named_props.get("投递") or "").strip()
        company_url = (named_props.get("link") or "").strip()
        source_url = (named_props.get("来源") or "").strip()

        canonical_url = apply_url or company_url or source_url
        if canonical_url and not canonical_url.startswith("http"):
            canonical_url = ""
        if not canonical_url:
            canonical_url = f"https://abetterweb3.notion.site/{bid.replace('-', '')}"

        location = named_props.get("办公区域", "").strip()
        remote_text = named_props.get("远程", "").strip().lower()
        remote_type = "remote" if remote_text in {"yes", "true", "1", "☑", "✅"} else "unknown"

        description_parts = [
            named_props.get("岗位需求", "").strip(),
            named_props.get("待遇/工作环境", "").strip(),
            named_props.get("投递", "").strip(),
        ]
        description = "\n".join([p for p in description_parts if p])[:4000]
        created_ms = value.get("created_time")
        posted_at = None
        if isinstance(created_ms, (int, float)) and created_ms > 0:
            posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).replace(tzinfo=None)

        jobs.append(
            NormalizedJob(
                source_job_id=bid,
                canonical_url=canonical_url,
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                employment_type="unknown",
                description=description,
                posted_at=posted_at,
                raw_payload={
                    "site": "abetterweb3",
                    "company_url": company_url,
                    "source_url": source_url,
                },
            )
        )

    return jobs


class ABetterWeb3Adapter(SourceAdapter):
    source_name = "abetterweb3"

    def fetch(self) -> list[NormalizedJob]:
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            cached = client.post(
                f"{NOTION_API_BASE}/loadCachedPageChunk",
                json={
                    "pageId": PAGE_ID,
                    "limit": 100,
                    "cursor": {"stack": []},
                    "chunkNumber": 0,
                    "verticalColumns": False,
                },
            )
            cached.raise_for_status()
            record_map = cached.json().get("recordMap") or {}
            collection_id, view_id, schema = _extract_collection_and_view(record_map)

            query = client.post(
                f"{NOTION_API_BASE}/queryCollection",
                json={
                    "collection": {"id": collection_id},
                    "collectionView": {"id": view_id},
                    "loader": {
                        "reducers": {"results": {"type": "results", "limit": 120}},
                        "sort": [],
                        "searchQuery": "",
                        "userTimeZone": "Asia/Shanghai",
                        "userLocale": "en",
                    },
                    "query": {"aggregate": []},
                },
            )
            query.raise_for_status()
            result = query.json().get("result") or {}
            reducers = result.get("reducerResults") or {}
            rows = (reducers.get("results") or {}).get("blockIds") or []
            if not rows:
                rows = (reducers.get("collection_group_results") or {}).get("blockIds") or []
            if not rows:
                return []

            requests = [{"table": "block", "id": bid, "version": -1} for bid in rows[:120]]
            sync = client.post(f"{NOTION_API_BASE}/syncRecordValues", json={"requests": requests})
            sync.raise_for_status()
            blocks = (sync.json().get("recordMap") or {}).get("block") or {}

        return _build_jobs_from_blocks(blocks, collection_id, schema)[:80]
