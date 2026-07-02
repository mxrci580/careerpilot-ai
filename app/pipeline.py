import json
from google.adk import Agent, Runner
from google.adk.apps.app import App
from google.adk.sessions import InMemorySessionService
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

# Reusable exponential backoff retry decorator for Google API calls (retries on 503/429)
gemini_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=15),
    reraise=True
)

from app.schemas import UserProfile, JobMatchResultsList

# ==========================================
# 1. AGENT 1: RESUME PARSING PIPELINE
# ==========================================
PARSER_INSTRUCTION = (
    "You are a professional Resume Extraction Agent. Your job is to extract the candidate's name, "
    "skills, and past work experiences from raw resume text. Output your results exactly in the "
    "UserProfile JSON format. Do not add any extra text outside the JSON."
)

@gemini_retry
async def parse_resume(raw_resume_text: str) -> UserProfile:
    """Takes raw resume text and parses it into a structured UserProfile object."""
    agent = Agent(
        name="ResumeParserAgent",
        model="gemini-3.5-flash",
        output_schema=UserProfile,
        instruction=PARSER_INSTRUCTION
    )
    
    app = App(name="ParserApp", root_agent=agent)
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service, auto_create_session=True)
    
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=raw_resume_text)]
    )
    
    accumulated_text = ""
    async for event in runner.run_async(
        user_id="pipeline_user",
        session_id="parse_trans",
        new_message=new_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    accumulated_text += part.text
                    
    return UserProfile.model_validate_json(accumulated_text)

# ==========================================
# 2. AGENT 2: JOB MATCHING & RANKING PIPELINE
# ==========================================
MATCHER_INSTRUCTION = (
    "You are a Senior Technical Recruiter and Job Matcher. Your task is to compare a candidate's "
    "profile (name, skills, experiences) with a list of available jobs.\n\n"
    
    "For each job provided, you must:\n"
    "1. Calculate an alignment match score (0-100).\n"
    "2. Identify matching skills.\n"
    "3. Identify missing skills required by the job.\n"
    "4. Explain the fit score in 2-3 sentences.\n"
    "5. Provide actionable, ethical advice to optimize the resume for this role.\n\n"
    
    "Output your evaluation exactly in the JobMatchResultsList JSON format."
)

@gemini_retry
async def match_jobs(profile: UserProfile, jobs_list_str: str) -> JobMatchResultsList:
    """Evaluates and ranks a list of jobs against the user's profile."""
    agent = Agent(
        name="JobMatcherAgent",
        model="gemini-3.5-flash",
        output_schema=JobMatchResultsList,
        instruction=MATCHER_INSTRUCTION
    )
    
    app = App(name="MatcherApp", root_agent=agent)
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service, auto_create_session=True)
    
    # We construct a comparative prompt for the matcher
    user_profile_json = profile.model_dump_json(indent=2)
    prompt = (
        f"Candidate Profile:\n{user_profile_json}\n\n"
        f"Available Jobs:\n{jobs_list_str}\n\n"
        f"Evaluate all available jobs against this candidate profile."
    )
    
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    )
    
    accumulated_text = ""
    async for event in runner.run_async(
        user_id="pipeline_user",
        session_id="match_trans",
        new_message=new_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    accumulated_text += part.text
                    
    return JobMatchResultsList.model_validate_json(accumulated_text)

# ==========================================
# 3. AGENT 3: COVER LETTER GENERATION PIPELINE
# ==========================================
WRITER_INSTRUCTION = (
    "You are a professional Resume Editor and Cover Letter Writer. Your job is to write a highly "
    "persuasive, customized cover letter for a candidate applying to a specific job.\n\n"
    
    "Guidelines:\n"
    "- Match the candidate's existing experience to the job requirements.\n"
    "- Do not fabricate skills or experience that the candidate does not have.\n"
    "- Keep the tone professional, enthusiastic, and confident.\n"
    "- Do not output JSON. Output a clean, ready-to-use cover letter text document."
)

@gemini_retry
async def generate_cover_letter(profile: UserProfile, job_title: str, company: str, job_desc: str) -> str:
    """Generates a tailored cover letter for a specific job description."""
    agent = Agent(
        name="CoverLetterAgent",
        model="gemini-3.5-flash",
        # No output_schema since we want a formatted text document
        instruction=WRITER_INSTRUCTION
    )
    
    app = App(name="WriterApp", root_agent=agent)
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service, auto_create_session=True)
    
    user_profile_json = profile.model_dump_json(indent=2)
    prompt = (
        f"Candidate Profile:\n{user_profile_json}\n\n"
        f"Job Details:\n"
        f"- Title: {job_title}\n"
        f"- Company: {company}\n"
        f"- Description: {job_desc}\n\n"
        f"Write a customized cover letter for this candidate applying to this job."
    )
    
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    )
    
    accumulated_text = ""
    async for event in runner.run_async(
        user_id="pipeline_user",
        session_id="write_trans",
        new_message=new_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    accumulated_text += part.text
                    
    return accumulated_text
