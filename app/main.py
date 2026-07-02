import io
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pypdf
from sqlalchemy import select

from app.db import init_db, search_jobs_in_db, async_session, JobModel, add_bookmark_to_db, get_bookmarked_jobs_from_db
from app.schemas import UserProfile, JobMatchResultsList
from app.pipeline import parse_resume, match_jobs, generate_cover_letter
from app.fetcher import fetch_and_store_jobs

# 1. Initialize FastAPI Application
app = FastAPI(
    title="CareerPilot API",
    description="Backend API services for CareerPilot resume parsing, job matching, and cover letter generation.",
    version="1.0.0"
)

# 2. Configure CORS (Cross-Origin Resource Sharing)
# This allows our local Web UI (running in a browser) to securely make calls to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any origin (perfect for local development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# 3. Database Initialization on Startup
@app.on_event("startup")
async def startup_event():
    print("FastAPI server starting. Initializing database...")
    await init_db()

# 4. Request Model for Cover Letter Generation
class CoverLetterRequest(BaseModel):
    profile: UserProfile
    job_title: str
    company: str
    description: str

# ==========================================
# ENDPOINTS
# ==========================================

@app.post("/api/parse-resume", response_model=UserProfile)
async def api_parse_resume(file: UploadFile = File(...)):
    """Uploads a PDF resume, extracts the text, and parses it into a structured user profile."""
    # Ensure it's a PDF
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # Read the binary stream of the uploaded file
        pdf_bytes = await file.read()
        pdf_file = io.BytesIO(pdf_bytes)
        
        # Extract text using pypdf
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="No readable text found inside the PDF.")
            
        # Run our ResumeParserAgent
        profile = await parse_resume(text)
        return profile
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")


@app.post("/api/match-jobs", response_model=JobMatchResultsList)
async def api_match_jobs(profile: UserProfile):
    """Takes a structured user profile, queries all jobs from SQLite, and returns ranked matching results."""
    try:
        # Fetch all database jobs formatted as a string (Stage 1 search)
        all_jobs_str = await search_jobs_in_db(query="")
        
        # Run our JobMatcherAgent (Stage 2 cognitive re-ranking)
        match_results = await match_jobs(profile, all_jobs_str)
        return match_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job matching failed: {str(e)}")


@app.post("/api/cover-letter")
async def api_cover_letter(req: CoverLetterRequest):
    """Takes a user profile and job details, and writes a tailored cover letter."""
    try:
        letter = await generate_cover_letter(
            profile=req.profile,
            job_title=req.job_title,
            company=req.company,
            job_desc=req.description
        )
        return {"cover_letter": letter}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")


@app.get("/api/jobs")
async def api_get_jobs(
    role: Optional[str] = None,
    experience: Optional[str] = None,
    location: Optional[str] = None,
    remote_pref: Optional[str] = None
):
    """Returns a list of job postings stored in the SQLite database, filtered by criteria."""
    try:
        async with async_session() as session:
            stmt = select(JobModel)
            
            # Apply filters dynamically
            if role:
                stmt = stmt.where(
                    JobModel.title.icontains(role) | 
                    JobModel.description.icontains(role) |
                    JobModel.requirements_json.icontains(role)
                )
            if location:
                stmt = stmt.where(JobModel.location.icontains(location))
                
            if remote_pref:
                if remote_pref == "remote":
                    stmt = stmt.where(
                        JobModel.location.icontains("remote") | 
                        JobModel.description.icontains("remote")
                    )
                elif remote_pref == "onsite_hybrid":
                    stmt = stmt.where(~JobModel.location.icontains("remote"))
                    
            if experience:
                if experience == "junior":
                    stmt = stmt.where(
                        JobModel.title.icontains("junior") | 
                        JobModel.title.icontains("intern") | 
                        JobModel.title.icontains("associate") |
                        JobModel.description.icontains("junior") |
                        JobModel.description.icontains("intern")
                    )
                elif experience == "senior":
                    stmt = stmt.where(
                        JobModel.title.icontains("senior") | 
                        JobModel.title.icontains("lead") | 
                        JobModel.title.icontains("staff") | 
                        JobModel.title.icontains("principal") |
                        JobModel.description.icontains("senior") |
                        JobModel.description.icontains("lead")
                    )
                elif experience == "mid":
                    # Mid-level: Exclude junior/intern and senior/lead/staff/principal
                    stmt = stmt.where(
                        ~JobModel.title.icontains("junior") &
                        ~JobModel.title.icontains("intern") &
                        ~JobModel.title.icontains("senior") &
                        ~JobModel.title.icontains("lead") &
                        ~JobModel.title.icontains("staff") &
                        ~JobModel.title.icontains("principal")
                    )
                    
            result = await session.execute(stmt)
            jobs = result.scalars().all()
            
            return [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "salary_range": j.salary_range,
                    "description": j.description,
                    "requirements": j.requirements
                } for j in jobs
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")


@app.post("/api/jobs/fetch")
async def api_fetch_live_jobs():
    """Fetches real remote tech jobs from Remotive API and saves them to the database."""
    try:
        count = await fetch_and_store_jobs()
        return {"status": "success", "new_jobs_added": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job ingestion failed: {str(e)}")


# 4.5 Bookmarking API routes
class BookmarkCreate(BaseModel):
    job_id: int


@app.post("/api/bookmarks")
async def api_add_bookmark(req: BookmarkCreate):
    """Bookmarks a job listing for the default user."""
    try:
        success = await add_bookmark_to_db(user_id="default_user", job_id=req.job_id)
        if not success:
            return {"status": "already_bookmarked", "message": "Job is already bookmarked."}
        return {"status": "success", "message": "Job bookmarked successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bookmark job: {str(e)}")


@app.get("/api/bookmarks")
async def api_get_bookmarks():
    """Returns a list of all jobs bookmarked by the default user."""
    try:
        jobs = await get_bookmarked_jobs_from_db(user_id="default_user")
        return [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "salary_range": j.salary_range,
                "description": j.description,
                "requirements": j.requirements
            } for j in jobs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bookmarks: {str(e)}")


# 5. Serve static files for the frontend UI
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
