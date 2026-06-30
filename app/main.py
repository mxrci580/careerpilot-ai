import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pypdf
from sqlalchemy import select

from app.db import init_db, search_jobs_in_db, async_session, JobModel
from app.schemas import UserProfile, JobMatchResultsList
from app.pipeline import parse_resume, match_jobs, generate_cover_letter

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
async def api_get_jobs():
    """Returns a list of all job postings stored in the SQLite database."""
    try:
        async with async_session() as session:
            stmt = select(JobModel)
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

# 5. Serve static files for the frontend UI
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
