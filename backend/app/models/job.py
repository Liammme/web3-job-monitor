from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_id", "source_job_id", name="uq_jobs_source_sourcejob"),
        UniqueConstraint("source_id", "fallback_hash", name="uq_jobs_source_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    fallback_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    canonical_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    remote_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
