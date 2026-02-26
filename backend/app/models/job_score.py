from __future__ import annotations
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class JobScore(Base):
    __tablename__ = "job_scores"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    keyword_score: Mapped[float] = mapped_column(Float, nullable=False)
    seniority_score: Mapped[float] = mapped_column(Float, nullable=False)
    remote_bonus: Mapped[float] = mapped_column(Float, nullable=False)
    region_bonus: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
