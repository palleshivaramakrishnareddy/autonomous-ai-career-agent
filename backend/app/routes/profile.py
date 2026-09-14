import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ProfileORM, CandidateProfileSchema, utcnow

router = APIRouter(prefix="/api/profile", tags=["profile"])

def serialize_profile(p: ProfileORM) -> dict:
    return {
        "id": p.id,
        "full_name": p.full_name,
        "email": p.email,
        "phone": p.phone,
        "location": p.location,
        "portfolio_url": p.portfolio_url or "",
        "linkedin_url": p.linkedin_url or "",
        "github_url": p.github_url or "",
        "target_roles": json.loads(p.target_roles_json or "[]"),
        "skills": json.loads(p.skills_json or "[]"),
        "experience_years": p.experience_years,
        "min_salary": p.min_salary,
        "remote_preference": p.remote_preference,
        "bio_summary": p.bio_summary,
        "work_experience": json.loads(p.work_experience_json or "[]"),
        "education": json.loads(p.education_json or "[]"),
        "excluded_keywords": json.loads(p.excluded_keywords_json or "[]"),
        "updated_at": p.updated_at.isoformat() if p.updated_at else None
    }

@router.get("")
def get_candidate_profile(db: Session = Depends(get_db)):
    profile = db.query(ProfileORM).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return serialize_profile(profile)

@router.put("")
def update_candidate_profile(payload: CandidateProfileSchema, db: Session = Depends(get_db)):
    profile = db.query(ProfileORM).first()
    if not profile:
        profile = ProfileORM()
        db.add(profile)

    profile.full_name = payload.full_name
    profile.email = payload.email
    profile.phone = payload.phone
    profile.location = payload.location
    profile.portfolio_url = payload.portfolio_url or ""
    profile.linkedin_url = payload.linkedin_url or ""
    profile.github_url = payload.github_url or ""
    profile.target_roles_json = json.dumps(payload.target_roles)
    profile.skills_json = json.dumps(payload.skills)
    profile.experience_years = payload.experience_years
    profile.min_salary = payload.min_salary
    profile.remote_preference = payload.remote_preference
    profile.bio_summary = payload.bio_summary
    profile.work_experience_json = json.dumps([item.model_dump() for item in payload.work_experience])
    profile.education_json = json.dumps([item.model_dump() for item in payload.education])
    profile.excluded_keywords_json = json.dumps(payload.excluded_keywords)
    profile.updated_at = utcnow()

    db.commit()
    db.refresh(profile)
    return {"status": "success", "profile": serialize_profile(profile)}
