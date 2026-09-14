import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    ApplicationRecordORM, JobPostingORM, MatchAnalysisORM, utcnow
)
from .jobs import serialize_job

router = APIRouter(prefix="/api/applications", tags=["applications"])

def serialize_application(app: ApplicationRecordORM) -> dict:
    job = app.job
    match = None
    if job and job.matches:
        match = job.matches[0]

    return {
        "id": app.id,
        "job_id": app.job_id,
        "status": app.status,
        "tailored_resume": app.tailored_resume,
        "cover_letter": app.cover_letter,
        "screening_qa": json.loads(app.screening_qa_json or "[]"),
        "ats_score": app.ats_score,
        "notes": app.notes,
        "applied_date": app.applied_date.isoformat() if app.applied_date else None,
        "interview_date": app.interview_date.isoformat() if app.interview_date else None,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "job": serialize_job(job, match) if job else None
    }

@router.get("")
def list_applications(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ApplicationRecordORM)
    if status:
        query = query.filter(ApplicationRecordORM.status == status)
    records = query.order_by(ApplicationRecordORM.updated_at.desc()).all()
    return [serialize_application(r) for r in records]

@router.get("/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(ApplicationRecordORM).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application record not found")
    return serialize_application(app)

@router.put("/{app_id}")
def update_application(app_id: int, payload: dict, db: Session = Depends(get_db)):
    app = db.query(ApplicationRecordORM).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application record not found")

    if "status" in payload:
        new_status = payload["status"]
        app.status = new_status
        if new_status == "applied" and not app.applied_date:
            app.applied_date = utcnow()

    if "notes" in payload:
        app.notes = payload["notes"]

    if "tailored_resume" in payload:
        app.tailored_resume = payload["tailored_resume"]

    if "cover_letter" in payload:
        app.cover_letter = payload["cover_letter"]

    if "interview_date" in payload:
        val = payload["interview_date"]
        if val:
            try:
                app.interview_date = datetime.fromisoformat(val.replace("Z", "+00:00"))
            except:
                pass
        else:
            app.interview_date = None

    app.updated_at = utcnow()
    db.commit()
    db.refresh(app)
    return {"status": "success", "application": serialize_application(app)}

@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(ApplicationRecordORM).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application record not found")
    db.delete(app)
    db.commit()
    return {"status": "success", "deleted_id": app_id}
