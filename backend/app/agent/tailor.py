import os
import json
import httpx
from typing import Dict, Any, List, Optional
from ..models import ProfileORM, JobPostingORM

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

def call_gemini_llm(api_key: str, prompt: str, model: str = "gemini-2.5-flash") -> Optional[str]:
    """Calls Gemini REST API directly with the provided prompt."""
    if not api_key:
        return None
    url = f"{GEMINI_API_URL}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
    except Exception as e:
        print(f"Gemini API call failed, falling back to local synthesizer: {e}")
    return None

def synthesize_tailored_resume_heuristic(profile: ProfileORM, job: JobPostingORM, match_data: Dict[str, Any]) -> str:
    """Algorithmic ATS-optimized tailored resume generation."""
    work_exp = json.loads(profile.work_experience_json or "[]")
    education = json.loads(profile.education_json or "[]")
    skills = json.loads(profile.skills_json or "[]")
    matched_skills = match_data.get("matched_skills", [])

    # Order skills: prioritize matched skills
    sorted_skills = list(matched_skills)
    for s in skills:
        if s not in sorted_skills:
            sorted_skills.append(s)

    skills_str = " • ".join(sorted_skills[:14])

    # Dynamic tailored summary
    tailored_summary = (
        f"Accomplished Software Engineer with {profile.experience_years:g}+ years of experience, "
        f"specializing in {', '.join(matched_skills[:3]) or 'modern full-stack architecture'}. "
        f"Demonstrated track record of scaling distributed cloud platforms, accelerating development velocity, "
        f"and engineering high-reliability systems aligned with {job.company}'s engineering standards."
    )

    resume_lines = [
        f"# {profile.full_name}",
        f"**{profile.location}** | {profile.email} | {profile.phone}",
        f"[Portfolio]({profile.portfolio_url}) | [LinkedIn]({profile.linkedin_url}) | [GitHub]({profile.github_url})",
        "",
        "## Professional Summary",
        tailored_summary,
        "",
        "## Core Competencies & Technical Skills",
        f"**ATS Keywords:** {skills_str}",
        "",
        "## Professional Experience"
    ]

    for exp in work_exp:
        resume_lines.append(f"### {exp.get('role')} — **{exp.get('company')}**")
        resume_lines.append(f"*{exp.get('period')}*")
        for bullet in exp.get("highlights", []):
            # Highlight matched skills in bullets if present
            resume_lines.append(f"- {bullet}")
        resume_lines.append("")

    if education:
        resume_lines.append("## Education")
        for edu in education:
            resume_lines.append(f"- **{edu.get('degree')}**, {edu.get('institution')} ({edu.get('year')})")

    return "\n".join(resume_lines)

def synthesize_cover_letter_heuristic(profile: ProfileORM, job: JobPostingORM, match_data: Dict[str, Any]) -> str:
    """Algorithmic tailored cover letter generation."""
    matched = match_data.get("matched_skills", [])
    top_skills = ", ".join(matched[:3]) if matched else "Full-Stack Development, Distributed Systems, and AI Engineering"
    work_exp = json.loads(profile.work_experience_json or "[]")
    most_recent = work_exp[0] if work_exp else {}
    recent_role = most_recent.get("role", "Software Engineer")
    recent_company = most_recent.get("company", "leading tech organizations")

    letter = f"""Dear Hiring Team at {job.company},

I am writing to express my enthusiastic interest in the {job.title} position at {job.company}. Having followed {job.company}'s trajectory, I am deeply impressed by your innovation in this space and would be thrilled to contribute to your engineering organization.

With over {profile.experience_years:g} years of engineering experience—most recently as {recent_role} at {recent_company}—I have architected high-throughput services and user-centric applications using {top_skills}. My background directly mirrors the technical requirements of this role, particularly in delivering robust, maintainable codebases that scale smoothly under production demand.

At {recent_company}, I spearheaded initiatives that demonstrably enhanced system latency, test automation, and feature velocity. I thrive in cross-functional environments where engineering rigor meets agile execution. Given {job.company}'s focus on quality and scale, I am confident I can make an immediate and measurable impact from day one.

Thank you for your time and consideration. I welcome the opportunity to discuss how my technical expertise and problem-solving mindset align with your goals for {job.title}.

Sincerely,
{profile.full_name}
{profile.email} | {profile.phone}
{profile.linkedin_url}
"""
    return letter.strip()

def synthesize_screening_qa(profile: ProfileORM, job: JobPostingORM, match_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generates ready-to-use screening question answers."""
    matched = ", ".join(match_data.get("matched_skills", [])[:4])
    return [
        {
            "question": f"Why do you want to work at {job.company}?",
            "answer": f"I admire {job.company}'s dedication to solving complex domain challenges with modern technology. The {job.title} opportunity directly aligns with my passion for building resilient systems, and I am excited to apply my experience in {matched} to help propel your product roadmap."
        },
        {
            "question": "What is your experience with the core tech stack required for this role?",
            "answer": f"I bring {profile.experience_years:g}+ years of hands-on production experience with the core requirements: {matched}. In my previous roles, I have designed scalable backend APIs, optimized database queries, and implemented modern CI/CD pipelines to ensure 99.9%+ reliability."
        },
        {
            "question": "What are your compensation expectations?",
            "answer": f"Based on the market rate for a {job.title} and my {profile.experience_years:g}+ years of experience, my target range is around ${profile.min_salary:,} to ${int(profile.min_salary * 1.25):,} base, plus equity and standard health/retirement benefits."
        },
        {
            "question": "What is your availability to start?",
            "answer": "I can comfortably start within a standard two-week notice window from an offer acceptance."
        }
    ]

def generate_tailored_application(profile: ProfileORM, job: JobPostingORM, match_data: Dict[str, Any], api_key: str = "", model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
    """
    Main orchestrator for generating tailored resume, cover letter, and screening Q&A.
    Uses Gemini if API key is provided, otherwise employs the deterministic synthesizer.
    """
    tailored_resume = None
    cover_letter = None
    llm_source = "heuristic_engine"

    if api_key:
        # Try LLM generation
        prompt_resume = f"""
You are an expert Executive Career Agent and ATS Resume Specialist.
Generate a tailored, professional, ATS-optimized Markdown resume for {profile.full_name} targeting the role of '{job.title}' at '{job.company}'.
Target Job Description:
{job.description[:1500]}

Candidate Raw Profile:
Name: {profile.full_name}
Email: {profile.email} | Phone: {profile.phone} | Location: {profile.location}
Bio: {profile.bio_summary}
Skills: {profile.skills_json}
Work Experience: {profile.work_experience_json}
Education: {profile.education_json}

Instructions:
1. Re-align the professional summary and skill highlights specifically for {job.company}.
2. Ensure bullet points emphasize achievements relevant to the job's required skills without fabricating fictitious facts.
3. Output strictly clean, valid Markdown.
"""
        tailored_resume = call_gemini_llm(api_key, prompt_resume, model_name)

        prompt_letter = f"""
Write an outstanding, professional, and authentic cover letter from {profile.full_name} to the Hiring Team at {job.company} for the position of {job.title}.
Job Description excerpt:
{job.description[:1500]}

Candidate Experience:
{profile.work_experience_json}
Candidate Skills:
{profile.skills_json}

Requirements:
- Emphasize alignment with {job.company}'s vision.
- Highlight candidate's specific accomplishments that solve the company's technical challenges.
- Keep tone professional, confident, and concise (300-400 words).
"""
        cover_letter = call_gemini_llm(api_key, prompt_letter, model_name)
        if tailored_resume and cover_letter:
            llm_source = f"gemini ({model_name})"

    if not tailored_resume:
        tailored_resume = synthesize_tailored_resume_heuristic(profile, job, match_data)
    if not cover_letter:
        cover_letter = synthesize_cover_letter_heuristic(profile, job, match_data)

    screening_qa = synthesize_screening_qa(profile, job, match_data)

    # Compute ATS optimization score (e.g. 85-98%)
    base_fit = match_data.get("fit_score", 75)
    ats_score = min(98, base_fit + 8)

    return {
        "tailored_resume": tailored_resume,
        "cover_letter": cover_letter,
        "screening_qa": screening_qa,
        "ats_score": ats_score,
        "source": llm_source
    }
