import json
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..models import (
    ProfileORM, JobPostingORM, MatchAnalysisORM,
    ApplicationRecordORM, AgentConfigORM, ActivityLogORM, utcnow
)
from .scraper import scout_all_jobs
from .matcher import calculate_fit_score
from .tailor import generate_tailored_application

def log_agent_activity(db: Session, level: str, category: str, message: str, details: Dict[str, Any] = None):
    """Utility to append an agent thought/action log."""
    log = ActivityLogORM(
        timestamp=utcnow(),
        level=level,
        category=category,
        message=message,
        details_json=json.dumps(details or {})
    )
    db.add(log)
    db.commit()

def run_agent_cycle(db: Session, force_scout: bool = True) -> Dict[str, Any]:
    """
    Executes a complete autonomous cycle:
    1. Reads Candidate Profile and Agent Configuration.
    2. Scouts for new jobs across live/curated sources.
    3. Analyzes ATS fit score for all new or unscored postings.
    4. Auto-tailors application packages for postings meeting the threshold.
    5. Advances application states according to autonomy settings.
    """
    profile = db.query(ProfileORM).first()
    if not profile:
        return {"status": "error", "message": "No candidate profile found. Please create a profile first."}

    config = db.query(AgentConfigORM).first()
    if not config:
        config = AgentConfigORM()
        db.add(config)
        db.commit()

    log_agent_activity(
        db,
        level="info",
        category="scout",
        message=f"Agent scout initiated. Mode: {'Autonomous' if config.is_autonomous else 'Copilot'}. Min Threshold: {config.min_fit_threshold}%."
    )

    new_jobs_count = 0
    scouted_jobs = []
    if force_scout:
        scouted_jobs = scout_all_jobs(max_results=20)
        for j in scouted_jobs:
            existing = db.query(JobPostingORM).filter_by(external_id=j["external_id"]).first()
            if not existing:
                job_orm = JobPostingORM(
                    external_id=j["external_id"],
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    is_remote=j["is_remote"],
                    salary_min=j["salary_min"],
                    salary_max=j["salary_max"],
                    currency=j["currency"],
                    job_type=j["job_type"],
                    source=j["source"],
                    tags_json=json.dumps(j.get("tags", [])),
                    url=j["url"],
                    description=j["description"],
                    published_at=utcnow(),
                    created_at=utcnow()
                )
                db.add(job_orm)
                new_jobs_count += 1
        db.commit()

    # Find jobs that haven't been matched yet
    unmatched_jobs = db.query(JobPostingORM).outerjoin(MatchAnalysisORM).filter(MatchAnalysisORM.id == None).all()

    evaluated_count = 0
    high_match_count = 0
    tailored_count = 0

    for job in unmatched_jobs:
        evaluated_count += 1
        analysis = calculate_fit_score(profile, job)

        # Store match analysis
        match_orm = MatchAnalysisORM(
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
        db.add(match_orm)
        db.commit()

        if analysis["fit_score"] >= config.min_fit_threshold:
            high_match_count += 1
            log_agent_activity(
                db,
                level="action",
                category="match",
                message=f"High match found ({analysis['fit_score']}%): {job.title} at {job.company}.",
                details={"job_id": job.id, "fit_score": analysis["fit_score"], "matched_skills": analysis["matched_skills"][:5]}
            )

            # Check if auto-tailoring is enabled
            if config.auto_tailor:
                tailored = generate_tailored_application(
                    profile=profile,
                    job=job,
                    match_data=analysis,
                    api_key=config.gemini_api_key,
                    model_name=config.model_name
                )

                # Determine initial status
                app_status = "ready"
                if config.is_autonomous and config.auto_apply:
                    app_status = "applied"
                elif config.is_autonomous:
                    app_status = "ready"
                else:
                    app_status = "tailored"

                app_record = ApplicationRecordORM(
                    job_id=job.id,
                    status=app_status,
                    tailored_resume=tailored["tailored_resume"],
                    cover_letter=tailored["cover_letter"],
                    screening_qa_json=json.dumps(tailored["screening_qa"]),
                    ats_score=tailored["ats_score"],
                    notes=f"Auto-generated package. ATS Score: {tailored['ats_score']}%.",
                    applied_date=utcnow() if app_status == "applied" else None,
                    created_at=utcnow(),
                    updated_at=utcnow()
                )
                db.add(app_record)
                db.commit()
                tailored_count += 1

                log_agent_activity(
                    db,
                    level="success",
                    category="tailor",
                    message=f"Application tailored for {job.title} at {job.company}. Staged as '{app_status.upper()}'.",
                    details={"job_id": job.id, "ats_score": tailored["ats_score"], "source": tailored.get("source")}
                )

    config.last_run_at = utcnow()
    db.commit()

    summary_msg = (
        f"Cycle completed. Scouted {len(scouted_jobs)} listings ({new_jobs_count} new). "
        f"Evaluated {evaluated_count} jobs. Found {high_match_count} roles >= {config.min_fit_threshold}%. "
        f"Synthesized {tailored_count} tailored applications."
    )

    log_agent_activity(
        db,
        level="success",
        category="system",
        message=summary_msg
    )

    return {
        "status": "success",
        "scouted_total": len(scouted_jobs),
        "new_jobs": new_jobs_count,
        "evaluated_matches": evaluated_count,
        "high_matches": high_match_count,
        "tailored_applications": tailored_count,
        "summary": summary_msg
    }
