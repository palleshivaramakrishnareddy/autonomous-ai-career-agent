import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from ..models import utcnow

# Curated fallback jobs if external network feeds are temporarily unavailable or rate-limited
CURATED_OFFLINE_JOBS = [
    {
        "external_id": "curated-job-101",
        "title": "Principal AI Platform Architect",
        "company": "NeuroScale Labs",
        "location": "Remote (US / EU)",
        "is_remote": True,
        "salary_min": 170000,
        "salary_max": 215000,
        "currency": "USD",
        "job_type": "Full-time",
        "source": "curated",
        "tags": ["Python", "FastAPI", "LLM Integration", "Kubernetes", "Vector Databases", "Docker", "AWS"],
        "url": "https://careers.neuroscalelabs.io/principal-ai-architect",
        "description": "NeuroScale Labs is developing enterprise autonomous agent runtime fabrics. We are searching for a Principal AI Platform Architect to spearhead our multi-agent orchestration service. Requirements: 6+ years experience in Python, FastAPI, distributed systems, and LLM agent architecture."
    },
    {
        "external_id": "curated-job-102",
        "title": "Senior Full-Stack Engineer (React & Python)",
        "company": "Loomis Health Tech",
        "location": "Remote",
        "is_remote": True,
        "salary_min": 145000,
        "salary_max": 180000,
        "currency": "USD",
        "job_type": "Full-time",
        "source": "curated",
        "tags": ["React", "TypeScript", "Python", "FastAPI", "PostgreSQL", "Docker", "TailwindCSS"],
        "url": "https://loomishealth.com/careers/senior-full-stack",
        "description": "Loomis is transforming clinical trial workflows. As a Senior Full-Stack Engineer, you will build patient-facing React interfaces and high-security FastAPI backends. Requirements: 5+ years experience with React, TypeScript, Python, and relational databases."
    },
    {
        "external_id": "curated-job-103",
        "title": "Staff Cloud Infrastructure & DevOps Engineer",
        "company": "Apex Distributed",
        "location": "Remote",
        "is_remote": True,
        "salary_min": 160000,
        "salary_max": 195000,
        "currency": "USD",
        "job_type": "Full-time",
        "source": "curated",
        "tags": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "Python", "Prometheus"],
        "url": "https://apexdistributed.io/careers/staff-devops",
        "description": "Join our core infrastructure team managing multi-region Kubernetes clusters on AWS. Requirements: 6+ years in cloud infrastructure, Terraform, container orchestration, and continuous deployment."
    },
    {
        "external_id": "curated-job-104",
        "title": "Senior Frontend Engineer (Design Systems)",
        "company": "Kinetix Studio",
        "location": "Remote (Worldwide)",
        "is_remote": True,
        "salary_min": 135000,
        "salary_max": 165000,
        "currency": "USD",
        "job_type": "Full-time",
        "source": "curated",
        "tags": ["React", "TypeScript", "Next.js", "TailwindCSS", "CSS", "UI/UX"],
        "url": "https://kinetix.studio/careers/senior-frontend",
        "description": "Kinetix is building creative tooling for digital artists. Looking for a skilled Senior Frontend Engineer with high craft in React, TypeScript, and micro-interactions."
    }
]

def fetch_jobs_from_remoteok(limit: int = 15) -> List[Dict[str, Any]]:
    """Fetches real-time job listings from RemoteOK public API."""
    jobs = []
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "CareerPilotAI/1.0 (JobMatchAgent)"}
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # RemoteOK first item is metadata/legal banner
                items = [item for item in data if isinstance(item, dict) and "id" in item]
                for item in items[:limit]:
                    job_id = f"remoteok-{item.get('id')}"
                    title = item.get("position") or item.get("title", "Software Engineer")
                    company = item.get("company", "Innovative Tech Co")
                    location = item.get("location") or "Remote"
                    url_link = item.get("url") or f"https://remoteok.com/l/{item.get('id')}"
                    tags = item.get("tags") or []
                    description = item.get("description") or f"Exciting position at {company} for {title}."

                    # Parse salary if present
                    salary_min = None
                    salary_max = None
                    if "salary_min" in item and item["salary_min"]:
                        try:
                            salary_min = int(item["salary_min"])
                        except:
                            pass
                    if "salary_max" in item and item["salary_max"]:
                        try:
                            salary_max = int(item["salary_max"])
                        except:
                            pass

                    jobs.append({
                        "external_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "is_remote": True,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "currency": "USD",
                        "job_type": "Full-time",
                        "source": "remoteok",
                        "tags": tags,
                        "url": url_link,
                        "description": description
                    })
    except Exception as e:
        print(f"Failed to fetch RemoteOK jobs: {e}")
    return jobs

def fetch_jobs_from_arbeitnow(limit: int = 15) -> List[Dict[str, Any]]:
    """Fetches job listings from Arbeitnow public API."""
    jobs = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                for item in items[:limit]:
                    job_id = f"arbeitnow-{item.get('slug', item.get('title'))}"
                    jobs.append({
                        "external_id": job_id,
                        "title": item.get("title", "Engineer"),
                        "company": item.get("company_name", "Tech Corp"),
                        "location": item.get("location", "Remote"),
                        "is_remote": bool(item.get("remote", True)),
                        "salary_min": None,
                        "salary_max": None,
                        "currency": "USD",
                        "job_type": "Full-time",
                        "source": "arbeitnow",
                        "tags": item.get("tags", []),
                        "url": item.get("url", ""),
                        "description": item.get("description", "")
                    })
    except Exception as e:
        print(f"Failed to fetch Arbeitnow jobs: {e}")
    return jobs

def scout_all_jobs(max_results: int = 25) -> List[Dict[str, Any]]:
    """Aggregates job listings across multiple live sources with curated fallback."""
    aggregated = []
    seen_ids = set()

    # 1. Try RemoteOK
    remoteok_jobs = fetch_jobs_from_remoteok(limit=12)
    for j in remoteok_jobs:
        if j["external_id"] not in seen_ids:
            seen_ids.add(j["external_id"])
            aggregated.append(j)

    # 2. Try Arbeitnow
    arbeit_jobs = fetch_jobs_from_arbeitnow(limit=10)
    for j in arbeit_jobs:
        if j["external_id"] not in seen_ids:
            seen_ids.add(j["external_id"])
            aggregated.append(j)

    # 3. If live sources yielded fewer than 5 results (e.g. offline or rate-limited), include curated jobs
    if len(aggregated) < 5:
        for j in CURATED_OFFLINE_JOBS:
            if j["external_id"] not in seen_ids:
                seen_ids.add(j["external_id"])
                aggregated.append(j)

    return aggregated[:max_results]
