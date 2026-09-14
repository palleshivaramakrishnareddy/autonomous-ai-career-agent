import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    AgentConfigORM, ActivityLogORM, AgentConfigSchema, utcnow
)
from ..agent.orchestrator import run_agent_cycle

router = APIRouter(prefix="/api/agent", tags=["agent"])

@router.get("/config")
def get_agent_config(db: Session = Depends(get_db)):
    config = db.query(AgentConfigORM).first()
    if not config:
        config = AgentConfigORM()
        db.add(config)
        db.commit()

    return {
        "is_autonomous": config.is_autonomous,
        "min_fit_threshold": config.min_fit_threshold,
        "auto_tailor": config.auto_tailor,
        "auto_apply": config.auto_apply,
        "scan_interval_minutes": config.scan_interval_minutes,
        "gemini_api_key": config.gemini_api_key or "",
        "has_api_key": bool(config.gemini_api_key),
        "model_name": config.model_name or "gemini-2.5-flash",
        "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None,
        "target_keywords": json.loads(config.target_keywords_json or "[]")
    }

@router.put("/config")
def update_agent_config(payload: dict, db: Session = Depends(get_db)):
    config = db.query(AgentConfigORM).first()
    if not config:
        config = AgentConfigORM()
        db.add(config)

    if "is_autonomous" in payload:
        config.is_autonomous = bool(payload["is_autonomous"])
    if "min_fit_threshold" in payload:
        config.min_fit_threshold = int(payload["min_fit_threshold"])
    if "auto_tailor" in payload:
        config.auto_tailor = bool(payload["auto_tailor"])
    if "auto_apply" in payload:
        config.auto_apply = bool(payload["auto_apply"])
    if "scan_interval_minutes" in payload:
        config.scan_interval_minutes = int(payload["scan_interval_minutes"])
    if "gemini_api_key" in payload:
        config.gemini_api_key = payload["gemini_api_key"].strip()
    if "model_name" in payload:
        config.model_name = payload["model_name"]
    if "target_keywords" in payload:
        config.target_keywords_json = json.dumps(payload["target_keywords"])

    db.commit()
    db.refresh(config)

    return {
        "status": "success",
        "config": {
            "is_autonomous": config.is_autonomous,
            "min_fit_threshold": config.min_fit_threshold,
            "auto_tailor": config.auto_tailor,
            "auto_apply": config.auto_apply,
            "scan_interval_minutes": config.scan_interval_minutes,
            "has_api_key": bool(config.gemini_api_key),
            "model_name": config.model_name,
            "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None
        }
    }

@router.post("/run")
def trigger_agent_run(db: Session = Depends(get_db)):
    """Triggers an autonomous job scouting and tailoring run."""
    result = run_agent_cycle(db, force_scout=True)
    return result

@router.get("/logs")
def get_activity_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(ActivityLogORM).order_by(ActivityLogORM.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "level": l.level,
            "category": l.category,
            "message": l.message,
            "details": json.loads(l.details_json or "{}")
        }
        for l in logs
    ]

@router.delete("/logs")
def clear_activity_logs(db: Session = Depends(get_db)):
    db.query(ActivityLogORM).delete()
    db.commit()
    return {"status": "success", "message": "Activity logs cleared"}
