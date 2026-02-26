from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crawlers.adapters.abetterweb3 import _build_jobs_from_blocks, _extract_collection_and_view
from app.crawlers.adapters.dejob import _build_jobs
from app.crawlers.registry import ADAPTERS
from app.db.database import Base
from app.models import setting as _setting_model  # ensure settings table is registered
from app.models.source import Source
from app.services import seed


def test_dejob_build_jobs_extracts_fields():
    jobs = _build_jobs(
        [
            {
                "topicId": 1001,
                "positionName": "Quant Developer",
                "company": "Arkstream Capital",
                "companyWebsite": "https://arkstream.capital/",
                "location": "Singapore",
                "officeModeName": "Remote",
                "workTypeName": "Full Time",
                "url": "https://dejob.ai/jobDetail?id=1001",
                "createTime": 1772023936179,
                "content": "desc",
            }
        ]
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Quant Developer"
    assert jobs[0].company == "Arkstream Capital"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].raw_payload["company_url"] == "https://arkstream.capital/"


def test_abetterweb3_helpers_extract_company_and_job():
    record_map = {
        "collection": {
            "cid": {
                "value": {
                    "schema": {
                        "title": {"name": "项目/公司"},
                        "job": {"name": "岗位需求"},
                        "src": {"name": "来源"},
                    }
                }
            }
        },
        "collection_view": {
            "vid": {"value": {"type": "table", "source_collection_id": "cid", "name": "最近编辑"}}
        },
    }

    cid, vid, schema = _extract_collection_and_view(record_map)
    assert cid == "cid"
    assert vid == "vid"

    blocks = {
        "bid1": {
            "value": {
                "id": "bid1",
                "type": "page",
                "parent_table": "collection",
                "parent_id": "cid",
                "properties": {
                    "title": [["Binance"]],
                    "job": [["Protocol Engineer"]],
                    "src": [["https://example.com/source"]],
                },
            }
        }
    }

    jobs = _build_jobs_from_blocks(blocks, cid, schema)
    assert len(jobs) == 1
    assert jobs[0].company == "Binance"
    assert jobs[0].title == "Protocol Engineer"


def test_registry_uses_new_sources_and_removes_remote3():
    assert "dejob" in ADAPTERS
    assert "abetterweb3" in ADAPTERS
    assert "remote3" not in ADAPTERS


def test_seed_adds_new_sources_and_disables_remote3(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(seed, "SessionLocal", TestingSession)

    db = TestingSession()
    db.add(Source(name="remote3", base_url="https://remote3.co", enabled=True, crawl_config={}))
    db.commit()
    db.close()

    seed.seed_sources_if_empty()

    db = TestingSession()
    src = {row.name: row for row in db.query(Source).all()}
    assert "dejob" in src
    assert "abetterweb3" in src
    assert src["remote3"].enabled is False
    db.close()
