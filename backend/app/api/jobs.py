from __future__ import annotations
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.database import get_db
from app.models.job import Job
from app.models.job_score import JobScore

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    q: str | None = None,
    source_id: int | None = None,
    high_priority: bool | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    query = db.query(Job, JobScore).outerjoin(JobScore, Job.id == JobScore.job_id)

    if q:
        like = f"%{q}%"
        query = query.filter((Job.title.ilike(like)) | (Job.company.ilike(like)) | (Job.description.ilike(like)))
    if source_id is not None:
        query = query.filter(Job.source_id == source_id)
    if high_priority is True:
        query = query.filter(JobScore.decision == "high")
    if high_priority is False:
        query = query.filter((JobScore.decision != "high") | (JobScore.decision.is_(None)))
    if start:
        query = query.filter(Job.collected_at >= start)
    if end:
        query = query.filter(Job.collected_at <= end)

    rows = query.order_by(Job.collected_at.desc()).offset(offset).limit(limit).all()
    data = []
    for job, score in rows:
        payload = {
            "id": job.id,
            "source_id": job.source_id,
            "source_job_id": job.source_job_id,
            "canonical_url": job.canonical_url,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote_type": job.remote_type,
            "employment_type": job.employment_type,
            "description": job.description,
            "posted_at": job.posted_at,
            "collected_at": job.collected_at,
            "is_new": job.is_new,
            "score": None,
        }
        if score:
            payload["score"] = {
                "total_score": score.total_score,
                "keyword_score": score.keyword_score,
                "seniority_score": score.seniority_score,
                "remote_bonus": score.remote_bonus,
                "region_bonus": score.region_bonus,
                "decision": score.decision,
                "scored_at": score.scored_at,
            }
        data.append(payload)
    return data


@router.get("/{job_id}")
def get_job(job_id: int, _: str = Depends(require_user), db: Session = Depends(get_db)):
    row = db.query(Job, JobScore).outerjoin(JobScore, Job.id == JobScore.job_id).filter(Job.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    job, score = row
    return {
        "id": job.id,
        "source_id": job.source_id,
        "source_job_id": job.source_job_id,
        "canonical_url": job.canonical_url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote_type": job.remote_type,
        "employment_type": job.employment_type,
        "description": job.description,
        "posted_at": job.posted_at,
        "collected_at": job.collected_at,
        "is_new": job.is_new,
        "score": {
            "total_score": score.total_score,
            "keyword_score": score.keyword_score,
            "seniority_score": score.seniority_score,
            "remote_bonus": score.remote_bonus,
            "region_bonus": score.region_bonus,
            "decision": score.decision,
            "scored_at": score.scored_at,
        }
        if score
        else None,
    }
