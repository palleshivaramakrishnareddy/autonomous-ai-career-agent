import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    JobPostingORM, MatchAnalysisORM, ProfileORM,
    ApplicationRecordORM, AgentConfigORM, utcnow
)
from ..agent.matcher import calculate_fit_score
from ..agent.tailor import generate_tailored_application, call_gemini_llm

router = APIRouter(prefix="/api/tailor", tags=["tailor"])

@router.post("/{job_id}")
def tailor_job_application(job_id: int, db: Session = Depends(get_db)):
    """Triggers on-demand synthesis of tailored resume and cover letter for a given job."""
    job = db.query(JobPostingORM).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = db.query(ProfileORM).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Candidate profile required.")

    config = db.query(AgentConfigORM).first()
    api_key = config.gemini_api_key if config else ""
    model_name = config.model_name if config else "gemini-2.5-flash"

    # Ensure match analysis is present
    match = db.query(MatchAnalysisORM).filter_by(job_id=job_id).first()
    if not match:
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
    else:
        analysis = {
            "fit_score": match.fit_score,
            "matched_skills": json.loads(match.matched_skills_json or "[]"),
            "missing_skills": json.loads(match.missing_skills_json or "[]"),
            "experience_match": match.experience_match,
            "compensation_match": match.compensation_match,
            "analysis_summary": match.analysis_summary,
            "recommendations": json.loads(match.recommendations_json or "[]")
        }

    # Generate tailored package
    tailored = generate_tailored_application(
        profile=profile,
        job=job,
        match_data=analysis,
        api_key=api_key,
        model_name=model_name
    )

    # Upsert application record
    app_record = db.query(ApplicationRecordORM).filter_by(job_id=job_id).first()
    if not app_record:
        app_record = ApplicationRecordORM(
            job_id=job_id,
            status="tailored",
            tailored_resume=tailored["tailored_resume"],
            cover_letter=tailored["cover_letter"],
            screening_qa_json=json.dumps(tailored["screening_qa"]),
            ats_score=tailored["ats_score"],
            notes=f"Generated tailored package (ATS Score: {tailored['ats_score']}%).",
            created_at=utcnow(),
            updated_at=utcnow()
        )
        db.add(app_record)
    else:
        app_record.tailored_resume = tailored["tailored_resume"]
        app_record.cover_letter = tailored["cover_letter"]
        app_record.screening_qa_json = json.dumps(tailored["screening_qa"])
        app_record.ats_score = tailored["ats_score"]
        app_record.updated_at = utcnow()

    db.commit()
    db.refresh(app_record)

    return {
        "status": "success",
        "application_id": app_record.id,
        "job_id": job.id,
        "ats_score": tailored["ats_score"],
        "tailored_resume": tailored["tailored_resume"],
        "cover_letter": tailored["cover_letter"],
        "screening_qa": tailored["screening_qa"],
        "source": tailored.get("source")
    }

@router.post("/{job_id}/interview-prep")
def generate_interview_prep(job_id: int, db: Session = Depends(get_db)):
    """Generates custom mock interview questions and STAR talking points for the role."""
    job = db.query(JobPostingORM).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = db.query(ProfileORM).first()
    config = db.query(AgentConfigORM).first()
    api_key = config.gemini_api_key if config else ""

    # Check if Gemini can be used
    if api_key:
        prompt = f"""
Create an executive interview preparation guide for a candidate interviewing for '{job.title}' at '{job.company}'.
Job Description: {job.description[:1000]}
Candidate Bio: {profile.bio_summary}
Candidate Skills: {profile.skills_json}

Return 3 behavioral questions and 2 technical system architecture questions.
For each, provide:
- The Question
- Strategic Intent (what the interviewer is probing for)
- Suggested STAR Answer blueprint tailored to the candidate's actual background.
Also provide 3 insightful questions the candidate should ask the hiring manager.
"""
        custom_content = call_gemini_llm(api_key, prompt, config.model_name if config else "gemini-2.5-flash")
        if custom_content:
            return {"status": "success", "guide": custom_content, "source": "gemini"}

    # Fallback high-yield interview prep guide
    guide = f"""# Interview Preparation Guide: {job.title} at {job.company}

## 1. Behavioral Question (Leadership & Ownership)
**Question**: "Tell me about a time you led a challenging technical initiative or architectural migration under tight deadlines."
- **Interviewer's Intent**: Assessing your ownership mindset, trade-off analysis, and cross-team communication.
- **STAR Blueprint**:
  - **Situation**: At your previous organization, high traffic or legacy bottlenecks impacted system performance.
  - **Task**: Architect a scalable migration (e.g. to FastAPI / microservices or containerized infrastructure) without customer downtime.
  - **Action**: Broke the project into incremental milestones, set up comprehensive automated tests, and mentored junior engineers.
  - **Result**: Successfully delivered on schedule with measurable latency reduction (e.g., 40%+) and zero production regressions.

## 2. Technical Question (System Reliability & Scalability)
**Question**: "How do you design a high-throughput API handling variable load and external dependency latency?"
- **Interviewer's Intent**: Evaluating your understanding of caching, rate-limiting, asynchronous processing, and fault tolerance.
- **Key Talking Points**:
  - Implement Redis caching for read-heavy hotspots.
  - Offload heavy tasks to background queues (Celery/RabbitMQ or async worker loops).
  - Enforce graceful degradation with circuit breakers and sensible timeout budgets.

## 3. Culture & Mission Alignment
**Question**: "Why do you want to join {job.company} specifically over other opportunities?"
- **Key Talking Points**:
  - Emphasize {job.company}'s specific impact in their industry.
  - Highlight your excitement about taking on end-to-end ownership in their engineering culture.

## Strategic Questions for YOU to Ask the Interviewer:
1. "What is the biggest technical roadblock currently facing the team working on this product?"
2. "How does engineering collaborate with product leadership when balancing technical debt against new feature delivery?"
3. "What does an extraordinary outcome look like for someone in this role after their first 6 months?"
"""
    return {"status": "success", "guide": guide, "source": "heuristic_curator"}
