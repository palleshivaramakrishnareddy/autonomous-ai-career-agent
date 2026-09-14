import json
from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    JobPostingORM, MatchAnalysisORM, ApplicationRecordORM, ProfileORM
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("")
def get_analytics(db: Session = Depends(get_db)):
    total_jobs = db.query(JobPostingORM).count()
    matches = db.query(MatchAnalysisORM).all()
    applications = db.query(ApplicationRecordORM).all()
    profile = db.query(ProfileORM).first()

    # Match score distribution
    high_match_count = sum(1 for m in matches if m.fit_score >= 80)
    medium_match_count = sum(1 for m in matches if 60 <= m.fit_score < 80)
    low_match_count = sum(1 for m in matches if m.fit_score < 60)

    # Application statuses
    status_counts = {
        "discovered": total_jobs,
        "tailored": 0,
        "ready": 0,
        "applied": 0,
        "interviewing": 0,
        "offer": 0,
        "rejected": 0
    }
    for app in applications:
        status = app.status.lower()
        if status in status_counts:
            status_counts[status] += 1

    # Skills demand aggregation across all scouted jobs
    candidate_skills = set(json.loads(profile.skills_json or "[]")) if profile else set()
    candidate_skills_lower = {s.lower() for s in candidate_skills}

    market_skill_counts = Counter()
    missing_skill_counts = Counter()

    for job in db.query(JobPostingORM).all():
        tags = json.loads(job.tags_json or "[]")
        for t in tags:
            tag_clean = t.strip().title()
            market_skill_counts[tag_clean] += 1
            if tag_clean.lower() not in candidate_skills_lower:
                missing_skill_counts[tag_clean] += 1

    top_demanded_skills = [
        {"skill": skill, "count": count, "has_skill": skill.lower() in candidate_skills_lower}
        for skill, count in market_skill_counts.most_common(10)
    ]

    top_missing_skills = [
        {"skill": skill, "count": count}
        for skill, count in missing_skill_counts.most_common(5)
    ]

    avg_fit = int(sum(m.fit_score for m in matches) / len(matches)) if matches else 0
    avg_ats = int(sum(a.ats_score for a in applications) / len(applications)) if applications else 0

    return {
        "total_jobs": total_jobs,
        "high_matches": high_match_count,
        "medium_matches": medium_match_count,
        "low_matches": low_match_count,
        "avg_fit_score": avg_fit,
        "avg_ats_score": avg_ats,
        "funnel": status_counts,
        "top_market_skills": top_demanded_skills,
        "top_missing_skills": top_missing_skills
    }
