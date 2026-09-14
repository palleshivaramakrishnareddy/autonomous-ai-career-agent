import pytest
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal, seed_default_data, ProfileORM, JobPostingORM
from backend.app.agent.matcher import calculate_fit_score
from backend.app.agent.tailor import generate_tailored_application
from backend.app.agent.orchestrator import run_agent_cycle

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    seed_default_data()

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_profile_api():
    # Test GET profile
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Alex Mercer"
    assert "Python" in data["skills"]

    # Test PUT profile update
    data["min_salary"] = 150000
    res_update = client.put("/api/profile", json=data)
    assert res_update.status_code == 200
    assert res_update.json()["profile"]["min_salary"] == 150000

def test_jobs_and_matching():
    res = client.get("/api/jobs")
    assert res.status_code == 200
    jobs = res.json()
    assert len(jobs) > 0

    first_job = jobs[0]
    assert "title" in first_job
    assert "match" in first_job
    assert first_job["match"] is not None
    assert 0 <= first_job["match"]["fit_score"] <= 100
    assert len(first_job["match"]["matched_skills"]) > 0

def test_manual_job_import():
    payload = {
        "title": "Lead Autonomous Agent Architect",
        "company": "DeepOrbit Labs",
        "location": "Remote",
        "is_remote": True,
        "salary_min": 175000,
        "salary_max": 210000,
        "description": "Architect autonomous AI workflows using Python, FastAPI, React, Docker, and LLMs.",
        "tags": ["Python", "FastAPI", "React", "Docker", "LLM Integration"]
    }
    res = client.post("/api/jobs", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["job"]["company"] == "DeepOrbit Labs"
    assert data["job"]["match"]["fit_score"] >= 80

def test_tailor_application():
    # Get any job
    jobs_res = client.get("/api/jobs")
    job_id = jobs_res.json()[0]["id"]

    res = client.post(f"/api/tailor/{job_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["tailored_resume"]) > 50
    assert len(data["cover_letter"]) > 50
    assert len(data["screening_qa"]) >= 3
    assert data["ats_score"] >= 70

def test_applications_lifecycle():
    # List applications
    res = client.get("/api/applications")
    assert res.status_code == 200
    apps = res.json()
    assert len(apps) > 0

    app_id = apps[0]["id"]

    # Update status to applied
    update_res = client.put(f"/api/applications/{app_id}", json={"status": "applied", "notes": "Applied via portal"})
    assert update_res.status_code == 200
    assert update_res.json()["application"]["status"] == "applied"
    assert update_res.json()["application"]["notes"] == "Applied via portal"

    # Advance to interviewing
    interview_res = client.put(f"/api/applications/{app_id}", json={"status": "interviewing", "interview_date": "2026-09-25T14:00:00Z"})
    assert interview_res.status_code == 200
    assert interview_res.json()["application"]["status"] == "interviewing"

def test_agent_cycle_and_logs():
    res = client.post("/api/agent/run")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    # Verify activity logs
    logs_res = client.get("/api/agent/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) > 0
    assert any("scout" in l["category"] or "tailor" in l["category"] or "system" in l["category"] for l in logs)

def test_analytics_api():
    res = client.get("/api/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_jobs"] > 0
    assert "funnel" in data
    assert "top_market_skills" in data
