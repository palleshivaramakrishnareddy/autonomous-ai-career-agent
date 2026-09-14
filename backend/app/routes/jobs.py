import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import JobPostingORM, MatchAnalysisORM, ProfileORM, ApplicationRecordORM, utcnow
from ..agent.scraper import scout_all_jobs
from ..agent.matcher import calculate_fit_score

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def serialize_job(job: JobPostingORM, match: Optional[MatchAnalysisORM] = None) -> dict:
    match_data = None
    if match:
        match_data = {
            "fit_score": match.fit_score,
            "matched_skills": json.loads(match.matched_skills_json or "[]"),
            "missing_skills": json.loads(match.missing_skills_json or "[]"),
            "experience_match": match.experience_match,
            "compensation_match": match.compensation_match,
            "analysis_summary": match.analysis_summary,
            "recommendations": json.loads(match.recommendations_json or "[]")
        }

    return {
        "id": job.id,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "is_remote": job.is_remote,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "job_type": job.job_type,
        "description": job.description,
        "url": job.url,
        "source": job.source,
        "tags": json.loads(job.tags_json or "[]"),
        "published_at": job.published_at.isoformat() if job.published_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "match": match_data
    }

@router.get("")
def list_jobs(
    q: Optional[str] = None,
    remote_only: bool = False,
    min_score: Optional[int] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(JobPostingORM, MatchAnalysisORM).outerjoin(
        MatchAnalysisORM, JobPostingORM.id == MatchAnalysisORM.job_id
    )

    if remote_only:
        query = query.filter(JobPostingORM.is_remote == True)

    if source:
        query = query.filter(JobPostingORM.source == source)

    if min_score is not None:
        query = query.filter(MatchAnalysisORM.fit_score >= min_score)

    results = query.order_by(
        MatchAnalysisORM.fit_score.desc().nullslast(),
        JobPostingORM.id.desc()
    ).all()

    profile = db.query(ProfileORM).first()

    output = []
    for job, match in results:
        # If match has not been computed yet and profile exists, compute dynamically
        if not match and profile:
            analysis = calculate_fit_score(profile, job)
            match = MatchAnalysisORM(
                job_id=job.id,
                fit_score=analysis["fit_score"],
                matched_skills_json=json.dumps(analysis["matched_skills"]),
                missing_skills_json=json.dumps(analysis["missing_skills"]),
                experience_match=analysis["experience_match"],
                compensation_match=analysis["compensation_match"],
                analysis_summary=analysis["analysis_summary"],
                recommendations_json=json.dumps(analysis["recommendations"]),
                created_at=utcnow()
            )
            db.add(match)
            db.commit()

        # Text search filtering
        if q:
            term = q.lower()
            if term not in job.title.lower() and term not in job.company.lower() and term not in job.description.lower():
                continue

        output.append(serialize_job(job, match))

    return output

@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobPostingORM).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match = db.query(MatchAnalysisORM).filter_by(job_id=job_id).first()
    if not match:
        profile = db.query(ProfileORM).first()
        if profile:
            analysis = calculate_fit_score(profile, job)
            match = MatchAnalysisORM(
                job_id=job.id,
                fit_score=analysis["fit_score"],
                matched_skills_json=json.dumps(analysis["matched_skills"]),
                missing_skills_json=json.dumps(analysis["missing_skills"]),
                experience_match=analysis["experience_match"],
                compensation_match=analysis["compensation_match"],
                analysis_summary=analysis["analysis_summary"],
                recommendations_json=json.dumps(analysis["recommendations"]),
                created_at=utcnow()
            )
            db.add(match)
            db.commit()

    return serialize_job(job, match)

@router.post("")
def add_custom_job(payload: dict, db: Session = Depends(get_db)):
    """Allows candidate to paste or import any job posting from LinkedIn, Greenhouse, etc."""
    title = payload.get("title", "").strip()
    company = payload.get("company", "").strip()
    description = payload.get("description", "").strip()

    if not title or not company or not description:
        raise HTTPException(status_code=400, detail="Title, company, and description are required.")

    ext_id = f"custom-{uuid.uuid4().hex[:10]}"
    job = JobPostingORM(
        external_id=ext_id,
        title=title,
        company=company,
        location=payload.get("location", "Remote"),
        is_remote=payload.get("is_remote", True),
        salary_min=payload.get("salary_min"),
        salary_max=payload.get("salary_max"),
        currency=payload.get("currency", "USD"),
        job_type=payload.get("job_type", "Full-time"),
        source=payload.get("source", "manual_import"),
        tags_json=json.dumps(payload.get("tags", [])),
        url=payload.get("url", ""),
        description=description,
        published_at=utcnow(),
        created_at=utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Compute immediate match score
    profile = db.query(ProfileORM).first()
    match = None
    if profile:
        analysis = calculate_fit_score(profile, job)
        match = MatchAnalysisORM(
            job_id=job.id,
            fit_score=analysis["fit_score"],
            matched_skills_json=json.dumps(analysis["matched_skills"]),
            missing_skills_json=json.dumps(analysis["missing_skills"]),
            experience_match=analysis["experience_match"],
            compensation_match=analysis["compensation_match"],
            analysis_summary=analysis["analysis_summary"],
            recommendations_json=json.dumps(analysis["recommendations"]),
            created_at=utcnow()
        )
        db.add(match)
        db.commit()

    return {"status": "success", "job": serialize_job(job, match)}

@router.post("/scout")
def trigger_scout(db: Session = Depends(get_db)):
    """Triggers immediate job discovery from external sources."""
    new_jobs = scout_all_jobs(max_results=20)
    added = 0
    for item in new_jobs:
        existing = db.query(JobPostingORM).filter_by(external_id=item["external_id"]).first()
        if not existing:
            job = JobPostingORM(
                external_id=item["external_id"],
                title=item["title"],
                company=item["company"],
                location=item["location"],
                is_remote=item["is_remote"],
                salary_min=item["salary_min"],
                salary_max=item["salary_max"],
                currency=item["currency"],
                job_type=item["job_type"],
                source=item["source"],
                tags_json=json.dumps(item.get("tags", [])),
                url=item["url"],
                description=item["description"],
                published_at=utcnow(),
                created_at=utcnow()
            )
            db.add(job)
            added += 1
    db.commit()
    return {"status": "success", "fetched": len(new_jobs), "new_jobs_added": added}

@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobPostingORM).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"status": "success", "deleted_id": job_id}
