from pydantic import BaseModel, Field
from typing import List

# 1. Schema for nested work experiences in the profile
class Experience(BaseModel):
    title: str = Field(description="Job title or role")
    company: str = Field(description="Company or organization name")
    duration: str = Field(description="Timeframe of the role, e.g. July 2024 - Present")

# 2. Schema representing the structured parsed resume
class UserProfile(BaseModel):
    name: str = Field(description="Candidate full name")
    skills: List[str] = Field(description="Key technical skills extracted from the resume")
    experience: List[Experience] = Field(description="List of past professional experiences")

# 3. Schema representing a single job match evaluation result
class JobMatchResult(BaseModel):
    job_id: int = Field(
        description="The unique database ID of the job listing"
    )
    match_score: int = Field(
        description="Alignment percentage from 0 (no match) to 100 (perfect match)"
    )
    matching_skills: List[str] = Field(
        description="Key skills the candidate already possesses that match the job description"
    )
    missing_skills: List[str] = Field(
        description="Skills requested by the job description that the candidate's resume lacks"
    )
    fit_explanation: str = Field(
        description="A concise 2-3 sentence summary explaining the matching score"
    )
    resume_advice: List[str] = Field(
        description="Actionable, ethical suggestions to improve the resume specifically for this role"
    )

# 4. Schema wrapper to return multiple job match evaluations
class JobMatchResultsList(BaseModel):
    matches: List[JobMatchResult] = Field(description="List of job match evaluations")
