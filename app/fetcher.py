import httpx
import json
import re
from typing import List
from sqlalchemy import select
from app.db import async_session, JobModel

REMOTIVE_URL = "https://remotive.com/api/remote-jobs?category=software-dev&limit=10"

def clean_html(raw_html: str) -> str:
    """Removes HTML tags and cleans up whitespace from job descriptions."""
    clean_r = re.compile('<.*?>')
    text = re.sub(clean_r, '', raw_html)
    # Decode basic HTML entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Clean up double newlines
    text = re.sub(r'\n+', '\n', text).strip()
    return text[:600] + "..." if len(text) > 600 else text

async def fetch_and_store_jobs() -> int:
    """Fetches real-world software developer jobs from Remotive API and inserts them into SQLite."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(REMOTIVE_URL, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching from Remotive: {e}")
            return 0
            
    jobs_list = data.get("jobs", [])
    added_count = 0
    
    async with async_session() as session:
        for job_data in jobs_list:
            title = job_data.get("title")
            company = job_data.get("company_name")
            
            # Check if this job (same title and company) already exists in database
            stmt = select(JobModel).where(
                JobModel.title == title,
                JobModel.company == company
            )
            result = await session.execute(stmt)
            existing = result.scalars().first()
            
            if existing:
                continue
                
            location = job_data.get("candidate_required_location", "Remote")
            salary = job_data.get("salary", "Not specified")
            raw_desc = job_data.get("description", "")
            description = clean_html(raw_desc)
            
            # Use 'tags' list or fallback to a standard list
            requirements = job_data.get("tags", ["Python", "JavaScript", "SQL"])
            # Clean requirement tags (keep only first 5 to keep re-ranking concise)
            requirements = [r.title() for r in requirements[:5]]
            
            db_job = JobModel(
                title=title,
                company=company,
                location=location,
                salary_range=salary,
                description=description,
                requirements_json=json.dumps(requirements)
            )
            session.add(db_job)
            added_count += 1
            
        await session.commit()
        
    return added_count

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("Fetching and storing live jobs from Remotive...")
        count = await fetch_and_store_jobs()
        print(f"Done. Added {count} new jobs to SQLite.")
        
    asyncio.run(main())
