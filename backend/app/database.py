import os
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import (
    Base, ProfileORM, JobPostingORM, MatchAnalysisORM,
    ApplicationRecordORM, AgentConfigORM, ActivityLogORM, utcnow
)

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DB_PATH = Path("/tmp") / "career_agent.db"
else:
    DB_PATH = Path(__file__).resolve().parent.parent / "career_agent.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_default_data():
    """Initializes tables and seeds initial realistic data if DB is empty."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if profile exists
        profile = db.query(ProfileORM).first()
        if not profile:
            sample_experience = [
                {
                    "company": "Cognitive Cloud Labs",
                    "role": "Lead Full-Stack AI Engineer",
                    "period": "2023 - Present",
                    "highlights": [
                        "Architected an agentic retrieval pipeline with FastAPI, LangGraph, and vector search, reducing customer query latency by 45%.",
                        "Led migration of frontend to Next.js 14 / TypeScript, improving Core Web Vitals score from 68 to 96.",
                        "Mentored a team of 5 engineers, establishing strict CI/CD linting, automated testing, and Dockerized staging environments."
                    ]
                },
                {
                    "company": "Apex Fintech Systems",
                    "role": "Senior Software Engineer",
                    "period": "2020 - 2023",
                    "highlights": [
                        "Designed and deployed mission-critical microservices in Python & Go processing over $12M daily transactional throughput.",
                        "Optimized PostgreSQL queries, partition strategies, and Redis caching layers, eliminating database CPU spikes during peak trading hours.",
                        "Collaborated directly with compliance and product teams to implement OAuth2 / OIDC security protocols."
                    ]
                },
                {
                    "company": "Nova Interactive",
                    "role": "Software Engineer",
                    "period": "2018 - 2020",
                    "highlights": [
                        "Developed dynamic dashboard interfaces in React and stateful REST APIs with Node.js & Express.",
                        "Created automated end-to-end test suites using Cypress and PyTest, increasing overall codebase test coverage to 88%."
                    ]
                }
            ]

            sample_education = [
                {
                    "institution": "University of California, Berkeley",
                    "degree": "B.S. in Computer Science",
                    "year": "2018"
                }
            ]

            profile = ProfileORM(
                full_name="Alex Mercer",
                email="alex.mercer.dev@example.com",
                phone="+1 (415) 890-2341",
                location="San Francisco, CA (Open to 100% Remote)",
                portfolio_url="https://alexmercer.dev",
                linkedin_url="https://linkedin.com/in/alex-mercer-engineer",
                github_url="https://github.com/alexmercer",
                target_roles_json=json.dumps([
                    "Senior Full-Stack Engineer",
                    "AI Systems Engineer",
                    "Senior Python / Backend Engineer",
                    "Lead Software Architect"
                ]),
                skills_json=json.dumps([
                    "Python", "FastAPI", "React", "TypeScript", "Next.js", "Node.js",
                    "PostgreSQL", "Docker", "Kubernetes", "AWS", "LLM Integration",
                    "Vector Databases", "Redis", "TailwindCSS", "Git", "REST APIs", "CI/CD"
                ]),
                experience_years=6.5,
                min_salary=145000,
                remote_preference="remote",
                bio_summary="High-impact Full-Stack & AI Systems Engineer with 6+ years of production experience building resilient cloud applications, autonomous AI agent pipelines, and high-performance web frontends. Passionate about LLM engineering, developer productivity, and clean system design.",
                work_experience_json=json.dumps(sample_experience),
                education_json=json.dumps(sample_education),
                excluded_keywords_json=json.dumps(["WordPress", "PHP 5", "Legacy VB.NET", "Crypto Ponzi", "Unpaid"])
            )
            db.add(profile)
            db.commit()

        # Check if config exists
        config = db.query(AgentConfigORM).first()
        if not config:
            config = AgentConfigORM(
                is_autonomous=False,
                min_fit_threshold=75,
                auto_tailor=True,
                auto_apply=False,
                scan_interval_minutes=60,
                gemini_api_key="",
                target_keywords_json=json.dumps(["python", "react", "fastapi", "ai", "full-stack", "typescript"])
            )
            db.add(config)
            db.commit()

        # Seed initial sample job postings if empty
        jobs_count = db.query(JobPostingORM).count()
        if jobs_count == 0:
            sample_jobs = [
                {
                    "external_id": "seed-job-1",
                    "title": "Senior Full-Stack Engineer (AI Applications)",
                    "company": "Synthetix AI",
                    "location": "Remote (US / Canada / Global)",
                    "is_remote": True,
                    "salary_min": 150000,
                    "salary_max": 185000,
                    "currency": "USD",
                    "job_type": "Full-time",
                    "source": "remoteok",
                    "tags": ["Python", "FastAPI", "React", "TypeScript", "LLM Integration", "AWS", "Docker"],
                    "url": "https://remoteok.com/job/synthetix-ai-senior-full-stack",
                    "description": """About Synthetix AI:
We are building the next-generation autonomous enterprise knowledge workspace powered by generative models. We are backed by premier venture firms and looking for a Senior Full-Stack Engineer to lead development of our agentic features.

Responsibilities:
- Build and scale responsive frontend interfaces using React, Next.js, and TypeScript.
- Develop robust backend microservices with Python and FastAPI handling high-concurrency LLM streaming requests.
- Integrate vector search databases and automated agent reasoning loops.
- Collaborate with product design and machine learning researchers to deploy intuitive UX.

Requirements:
- 5+ years of software engineering experience.
- Strong proficiency in Python, FastAPI, React, and TypeScript.
- Hands-on experience with cloud infrastructure (AWS or GCP) and Docker containers.
- Strong knowledge of relational databases (PostgreSQL) and caching (Redis).
- Passion for modern AI tools, agentic workflows, and clean code architecture.

Benefits:
- Competitive base salary ($150,000 - $185,000) + equity.
- 100% remote work freedom with flexible hours.
- Comprehensive health, dental, and vision insurance.
- Home office stipend and continuous learning budget."""
                },
                {
                    "external_id": "seed-job-2",
                    "title": "Senior Python / Backend Platform Engineer",
                    "company": "DataStream Cloud",
                    "location": "Remote (Worldwide)",
                    "is_remote": True,
                    "salary_min": 140000,
                    "salary_max": 170000,
                    "currency": "USD",
                    "job_type": "Full-time",
                    "source": "arbeitnow",
                    "tags": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "CI/CD", "Redis"],
                    "url": "https://arbeitnow.com/jobs/datastream-backend-engineer",
                    "description": """DataStream Cloud is an infrastructure platform powering real-time event analytics for Fortune 500 enterprises.

We are seeking a Senior Backend Engineer to architect data ingestion pipelines and core API gateways.

Key Duties:
- Design fault-tolerant distributed services using Python, AsyncIO, and FastAPI.
- Optimize high-throughput PostgreSQL queries and manage Redis distributed caching.
- Build automated testing and deployment pipelines using Docker, Kubernetes, and GitHub Actions.
- Ensure 99.99% uptime for core client-facing APIs.

Requirements:
- 5+ years experience in Python backend engineering.
- Deep expertise in PostgreSQL, query tuning, and database modeling.
- Solid background in containerization (Docker, Kubernetes).
- Familiarity with CI/CD and production monitoring (Prometheus, Grafana)."""
                },
                {
                    "external_id": "seed-job-3",
                    "title": "Lead Frontend / React Architect",
                    "company": "Veloce Design Systems",
                    "location": "San Francisco, CA / Remote",
                    "is_remote": True,
                    "salary_min": 160000,
                    "salary_max": 195000,
                    "currency": "USD",
                    "job_type": "Full-time",
                    "source": "remoteok",
                    "tags": ["React", "TypeScript", "Next.js", "TailwindCSS", "Design Systems"],
                    "url": "https://remoteok.com/job/veloce-react-architect",
                    "description": """Veloce is building the design system and component infrastructure used by hundreds of modern web apps.

Looking for a Lead Frontend Architect with deep expertise in React 18/19, TypeScript, and modern CSS frameworks like TailwindCSS.

Responsibilities:
- Guide frontend architecture across cross-functional product pods.
- Build high-performance, accessible, responsive component libraries.
- Optimize frontend bundle sizes and client-side rendering bottlenecks."""
                }
            ]

            for item in sample_jobs:
                job_orm = JobPostingORM(
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
                    tags_json=json.dumps(item["tags"]),
                    url=item["url"],
                    description=item["description"],
                    published_at=utcnow(),
                    created_at=utcnow()
                )
                db.add(job_orm)
            db.commit()

        # Seed initial activity log
        log_count = db.query(ActivityLogORM).count()
        if log_count == 0:
            log = ActivityLogORM(
                level="success",
                category="system",
                message="CareerPilot AI initialized successfully. Agent is armed and ready.",
                details_json=json.dumps({"initialized_at": str(utcnow())})
            )
            db.add(log)
            db.commit()

    finally:
        db.close()
