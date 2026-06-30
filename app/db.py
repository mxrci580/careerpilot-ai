import json
from typing import List, Optional
from sqlalchemy import String, Text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 1. Database Connection URL (configured for the async sqlite+aiosqlite driver)
DATABASE_URL = "sqlite+aiosqlite:///data/careerpilot.db"

# Create the async SQL engine and session maker
engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# 2. Define the Base ORM class
class Base(DeclarativeBase):
    pass

# 3. Define the Job Table Model
class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    salary_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # We store the list of requirements as a JSON string in this TEXT column
    requirements_json: Mapped[str] = mapped_column(Text, nullable=False)

    @property
    def requirements(self) -> List[str]:
        """Deserializes the JSON string back into a Python list."""
        try:
            return json.loads(self.requirements_json)
        except Exception:
            return []

# 4. Mock job listings to seed our database
MOCK_JOBS = [
    {
        "title": "Junior Python Developer",
        "company": "TechSoft Solutions",
        "location": "San Francisco, CA",
        "salary_range": "$90k - $110k",
        "description": "We are looking for a Junior Python Developer to assist with backend API integrations.",
        "requirements": ["Python", "Git", "REST APIs"]
    },
    {
        "title": "ML Engineer Intern",
        "company": "Cognitive AI",
        "location": "Remote",
        "salary_range": "$40 - $55 / hour",
        "description": "Join our AI research team as an ML Intern. Help build and fine-tune NLP models.",
        "requirements": ["Python", "PyTorch", "Git", "Machine Learning"]
    },
    {
        "title": "Frontend Engineer (React)",
        "company": "WebFlow Corp",
        "location": "New York, NY",
        "salary_range": "$120k - $140k",
        "description": "Build high-performance web applications using React, HTML5, and TailwindCSS.",
        "requirements": ["React", "JavaScript", "HTML", "CSS", "TailwindCSS"]
    },
    {
        "title": "Backend AI Developer",
        "company": "Apex Robotics",
        "location": "San Francisco, CA",
        "salary_range": "$130k - $160k",
        "description": "Build asynchronous Python microservices to coordinate robotic vision pipelines.",
        "requirements": ["Python", "SQL", "Docker", "FastAPI"]
    }
]

# 5. Initialize the database and seed it if empty
async def init_db():
    """Creates the tables and seeds them with mock jobs if they don't exist."""
    async with engine.begin() as conn:
        # Create all tables defined in our Base metadata
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        # Check if the jobs table is already populated
        result = await session.execute(select(JobModel))
        existing_jobs = result.scalars().all()
        
        if not existing_jobs:
            print("Seeding SQLite database with mock job listings...")
            for job in MOCK_JOBS:
                db_job = JobModel(
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    salary_range=job["salary_range"],
                    description=job["description"],
                    # Serialize the requirements list to a JSON string
                    requirements_json=json.dumps(job["requirements"])
                )
                session.add(db_job)
            await session.commit()
            print("Seeding complete.")
        else:
            print("Database already seeded. Skipping seeder.")

# 6. Expose the search query as a helper function (will be our Agent Tool)
async def search_jobs_in_db(query: str, location: Optional[str] = None) -> str:
    """Searches the SQLite database for jobs matching query keywords.

    Args:
        query: The search terms (e.g., 'python', 'react').
        location: Optional location filter (e.g., 'San Francisco', 'Remote').
    """
    async with async_session() as session:
        # We query the database for jobs
        stmt = select(JobModel)
        result = await session.execute(stmt)
        all_jobs = result.scalars().all()
        
        # Simple Python keyword search over the title, description, and requirements
        matches = []
        q = query.lower()
        loc = location.lower() if location else ""
        
        for job in all_jobs:
            # Check location match if location filter is passed
            if loc and loc not in job.location.lower():
                continue
                
            # Check keyword match in Title, Description, or Requirements
            in_title = q in job.title.lower()
            in_desc = q in job.description.lower()
            in_reqs = any(q in req.lower() for req in job.requirements)
            
            if in_title or in_desc or in_reqs:
                matches.append(job)
        
        # Format the output as a clean string for the Agent to read
        if not matches:
            return f"No jobs found matching '{query}'" + (f" in '{location}'" if location else "")
            
        output = [f"Found {len(matches)} matching job(s):"]
        for j in matches:
            reqs_str = ", ".join(j.requirements)
            salary = j.salary_range if j.salary_range else "Not specified"
            output.append(
                f"- Job ID: {j.id}\n"
                f"  Title: {j.title}\n"
                f"  Company: {j.company}\n"
                f"  Location: {j.location}\n"
                f"  Salary: {salary}\n"
                f"  Description: {j.description}\n"
                f"  Requirements: [{reqs_str}]\n"
            )
        return "\n".join(output)
