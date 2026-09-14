import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
)
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

# ==================== ORM MODELS ====================

class ProfileORM(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), default="Alex Mercer")
    email = Column(String(150), default="alex.mercer@example.com")
    phone = Column(String(50), default="+1 (555) 234-5678")
    location = Column(String(150), default="San Francisco, CA (Open to Remote)")
    portfolio_url = Column(String(255), default="https://alexmercer.dev")
    linkedin_url = Column(String(255), default="https://linkedin.com/in/alexmercer-dev")
    github_url = Column(String(255), default="https://github.com/alexmercer")
    target_roles_json = Column(Text, default='["Senior Full-Stack Engineer", "AI Application Engineer", "Backend Engineer"]')
    skills_json = Column(Text, default='["Python", "FastAPI", "React", "TypeScript", "Node.js", "PostgreSQL", "Docker", "AWS", "LLM Integration", "TailwindCSS"]')
    experience_years = Column(Float, default=6.0)
    min_salary = Column(Integer, default=140000)
    remote_preference = Column(String(50), default="remote")
    bio_summary = Column(Text, default="Versatile Full-Stack & AI Systems Engineer with 6+ years of experience designing scalable distributed web services, RESTful APIs, and modern interactive user interfaces. Passionate about agentic AI workflows, developer productivity, and clean architecture.")
    work_experience_json = Column(Text, default="[]")
    education_json = Column(Text, default="[]")
    excluded_keywords_json = Column(Text, default='["Wordpress", "PHP 5", "Legacy ColdFusion"]')
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class JobPostingORM(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(150), unique=True, index=True)
    title = Column(String(255), index=True)
    company = Column(String(255), index=True)
    location = Column(String(255), default="Remote")
    is_remote = Column(Boolean, default=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String(10), default="USD")
    job_type = Column(String(50), default="Full-time")
    description = Column(Text)
    url = Column(String(500))
    source = Column(String(50), default="remoteok")
    tags_json = Column(Text, default="[]")
    published_at = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    matches = relationship("MatchAnalysisORM", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("ApplicationRecordORM", back_populates="job", cascade="all, delete-orphan")

class MatchAnalysisORM(Base):
    __tablename__ = "match_analyses"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), index=True)
    fit_score = Column(Integer, default=0)  # 0 to 100
    matched_skills_json = Column(Text, default="[]")
    missing_skills_json = Column(Text, default="[]")
    experience_match = Column(String(50), default="moderate")
    compensation_match = Column(String(50), default="unspecified")
    analysis_summary = Column(Text, default="")
    recommendations_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=utcnow)

    job = relationship("JobPostingORM", back_populates="matches")

class ApplicationRecordORM(Base):
    __tablename__ = "application_records"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), index=True)
    status = Column(String(50), default="discovered")  # discovered, analyzing, tailored, ready, applied, interviewing, offer, rejected, archived
    tailored_resume = Column(Text, default="")
    cover_letter = Column(Text, default="")
    screening_qa_json = Column(Text, default="[]")
    ats_score = Column(Integer, default=0)
    notes = Column(Text, default="")
    applied_date = Column(DateTime, nullable=True)
    interview_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    job = relationship("JobPostingORM", back_populates="applications")

class AgentConfigORM(Base):
    __tablename__ = "agent_config"

    id = Column(Integer, primary_key=True)
    is_autonomous = Column(Boolean, default=False)  # False: Copilot, True: Full Auto
    min_fit_threshold = Column(Integer, default=75)
    auto_tailor = Column(Boolean, default=True)
    auto_apply = Column(Boolean, default=False)
    scan_interval_minutes = Column(Integer, default=60)
    gemini_api_key = Column(String(255), default="")
    model_name = Column(String(100), default="gemini-2.5-flash")
    last_run_at = Column(DateTime, nullable=True)
    target_keywords_json = Column(Text, default='["python", "react", "full stack", "ai", "engineer"]')

class ActivityLogORM(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utcnow)
    level = Column(String(20), default="info")  # info, success, warning, action
    category = Column(String(50), default="system")  # scout, match, tailor, apply, system
    message = Column(String(255))
    details_json = Column(Text, default="{}")


# ==================== PYDANTIC SCHEMAS ====================

class WorkExperienceItem(BaseModel):
    company: str
    role: str
    period: str
    highlights: List[str] = []

class EducationItem(BaseModel):
    institution: str
    degree: str
    year: str

class CandidateProfileSchema(BaseModel):
    id: Optional[int] = None
    full_name: str
    email: str
    phone: str
    location: str
    portfolio_url: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    target_roles: List[str] = []
    skills: List[str] = []
    experience_years: float = 5.0
    min_salary: int = 120000
    remote_preference: str = "remote"
    bio_summary: str = ""
    work_experience: List[WorkExperienceItem] = []
    education: List[EducationItem] = []
    excluded_keywords: List[str] = []

class JobPostingSchema(BaseModel):
    id: Optional[int] = None
    external_id: str
    title: str
    company: str
    location: str = "Remote"
    is_remote: bool = True
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    job_type: str = "Full-time"
    description: str
    url: str
    source: str = "remoteok"
    tags: List[str] = []
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class MatchAnalysisSchema(BaseModel):
    id: Optional[int] = None
    job_id: int
    fit_score: int
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    experience_match: str = "moderate"
    compensation_match: str = "unspecified"
    analysis_summary: str = ""
    recommendations: List[str] = []

class ScreeningQA(BaseModel):
    question: str
    answer: str

class ApplicationRecordSchema(BaseModel):
    id: Optional[int] = None
    job_id: int
    job: Optional[JobPostingSchema] = None
    status: str = "discovered"
    tailored_resume: str = ""
    cover_letter: str = ""
    screening_qa: List[ScreeningQA] = []
    ats_score: int = 0
    notes: str = ""
    applied_date: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AgentConfigSchema(BaseModel):
    is_autonomous: bool = False
    min_fit_threshold: int = 75
    auto_tailor: bool = True
    auto_apply: bool = False
    scan_interval_minutes: int = 60
    gemini_api_key: Optional[str] = ""
    model_name: str = "gemini-2.5-flash"
    last_run_at: Optional[datetime] = None
    target_keywords: List[str] = []

class ActivityLogSchema(BaseModel):
    id: int
    timestamp: datetime
    level: str
    category: str
    message: str
    details: Dict[str, Any] = {}
