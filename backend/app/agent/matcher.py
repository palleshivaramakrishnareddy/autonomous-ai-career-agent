import re
import json
from typing import Dict, Any, List, Set
from ..models import ProfileORM, JobPostingORM, MatchAnalysisSchema

COMMON_TECH_SKILLS = [
    "python", "fastapi", "django", "flask", "react", "next.js", "vue", "angular",
    "typescript", "javascript", "node.js", "express", "go", "golang", "rust",
    "java", "spring boot", "c++", "c#", ".net", "sql", "postgresql", "mysql",
    "mongodb", "redis", "elasticsearch", "docker", "kubernetes", "aws", "gcp",
    "azure", "terraform", "ci/cd", "github actions", "graphql", "rest api",
    "llm", "langchain", "langgraph", "vector databases", "pinecone", "chromadb",
    "tailwind", "tailwindcss", "html", "css", "kafka", "rabbitmq", "microservices"
]

def extract_keywords_from_text(text: str) -> Set[str]:
    """Extracts known tech skills and key words from text in a case-insensitive manner."""
    text_lower = text.lower()
    found = set()
    for skill in COMMON_TECH_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)
    return found

def calculate_fit_score(profile: ProfileORM, job: JobPostingORM) -> Dict[str, Any]:
    """
    Computes a multi-dimensional ATS fit score and breakdown between candidate and job.
    Returns:
      fit_score: int (0-100)
      matched_skills: list of str
      missing_skills: list of str
      experience_match: str ("strong", "moderate", "gap")
      compensation_match: str ("met", "below", "above", "unspecified")
      analysis_summary: str
      recommendations: list of str
    """
    # 1. Candidate skills
    candidate_skills_list = json.loads(profile.skills_json or "[]")
    candidate_skills_norm = {s.lower().strip() for s in candidate_skills_list}

    # 2. Job required skills (from tags + extracted from description)
    job_tags = json.loads(job.tags_json or "[]")
    job_desc_skills = extract_keywords_from_text(f"{job.title} {job.description}")
    for t in job_tags:
        job_desc_skills.add(t.lower().strip())

    if not job_desc_skills:
        # Fallback if no specific tech skills detected
        job_desc_skills = {"python", "git", "rest api"}

    matched_skills_set = candidate_skills_norm.intersection(job_desc_skills)
    missing_skills_set = job_desc_skills.difference(candidate_skills_norm)

    # Format properly capitalized for display
    skill_display_map = {s.lower(): s for s in candidate_skills_list + COMMON_TECH_SKILLS}
    matched_skills = [skill_display_map.get(s, s.title()) for s in sorted(matched_skills_set)]
    missing_skills = [skill_display_map.get(s, s.title()) for s in sorted(missing_skills_set)]

    # 3. Skills Score (Weight: 45%)
    skill_coverage = len(matched_skills_set) / max(len(job_desc_skills), 1)
    skills_score = min(100.0, skill_coverage * 100.0)

    # 4. Title / Role Match (Weight: 25%)
    target_roles = json.loads(profile.target_roles_json or "[]")
    job_title_lower = job.title.lower()
    title_score = 40.0  # base
    for role in target_roles:
        role_lower = role.lower()
        role_tokens = set(role_lower.split())
        title_tokens = set(job_title_lower.split())
        overlap = len(role_tokens.intersection(title_tokens))
        if overlap >= 2:
            title_score = 95.0
            break
        elif overlap >= 1:
            title_score = max(title_score, 75.0)

    # 5. Location / Remote Match (Weight: 15%)
    location_score = 80.0
    if profile.remote_preference == "remote":
        if job.is_remote or "remote" in job.location.lower():
            location_score = 100.0
        else:
            location_score = 30.0
    elif profile.remote_preference == "hybrid":
        location_score = 90.0 if (job.is_remote or "hybrid" in job.location.lower()) else 60.0
    else:
        location_score = 85.0

    # 6. Compensation Match (Weight: 15%)
    comp_match = "unspecified"
    comp_score = 80.0
    if job.salary_min or job.salary_max:
        max_sal = job.salary_max or job.salary_min or 0
        min_sal = job.salary_min or job.salary_max or 0
        if max_sal >= profile.min_salary:
            comp_match = "met"
            comp_score = 100.0
        elif max_sal >= (profile.min_salary * 0.9):
            comp_match = "near"
            comp_score = 80.0
        else:
            comp_match = "below"
            comp_score = 40.0

    # 7. Experience Level
    desc_lower = job.description.lower()
    experience_match = "strong"
    if "senior" in job_title_lower or "lead" in job_title_lower or "staff" in job_title_lower:
        if profile.experience_years >= 5.0:
            experience_match = "strong"
        elif profile.experience_years >= 3.0:
            experience_match = "moderate"
        else:
            experience_match = "gap"
    elif "junior" in job_title_lower or "entry" in job_title_lower:
        experience_match = "overqualified" if profile.experience_years > 5.0 else "strong"

    # Overall weighted score
    raw_fit = (
        (skills_score * 0.45) +
        (title_score * 0.25) +
        (location_score * 0.15) +
        (comp_score * 0.15)
    )

    fit_score = int(round(raw_fit))
    fit_score = max(10, min(99, fit_score))

    # Construct recommendations
    recommendations = []
    if missing_skills:
        top_missing = missing_skills[:3]
        recommendations.append(f"Highlight any adjacent experience with {', '.join(top_missing)} in the tailored cover letter.")
    if comp_match == "below":
        recommendations.append("Posted salary is below your target minimum threshold; consider negotiating equity/bonus.")
    if experience_match == "strong":
        recommendations.append("Strong seniority match: emphasize architectural leadership and measurable project impact.")

    summary = (
        f"{fit_score}% overall compatibility. Candidate matches {len(matched_skills)} core requirements "
        f"for {job.title} at {job.company}. Seniority alignment is rated {experience_match}."
    )

    return {
        "fit_score": fit_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience_match": experience_match,
        "compensation_match": comp_match,
        "analysis_summary": summary,
        "recommendations": recommendations
    }
