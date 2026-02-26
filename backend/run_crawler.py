from __future__ import annotations
from app.db.init_db import init_db
from app.db.database import SessionLocal
from app.services.crawl_service import run_crawl


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        result = run_crawl(db)
        print(result)
    finally:
        db.close()
